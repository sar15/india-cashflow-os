import hashlib
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Union

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from cashflow_os.api.auth import AuthPrincipal, ensure_org_access, require_roles
from cashflow_os.api.schemas import (
    ConfirmImportPayload,
    DesktopAgentHeartbeatRequest,
    DesktopAgentRegistrationRequest,
    ImportCreatePayload,
    ObligationSetupPayload,
    ScenarioSetupPayload,
    ZohoConnectRequest,
    ZohoExchangeRequest,
)
from cashflow_os.api.store import InMemoryStore
from cashflow_os.db.engine import dispose_engine, get_database_url, health_check as db_health_check, init_engine, is_postgres_available
from cashflow_os.db.repository import PostgresRepository
from cashflow_os.domain.models import (
    BankBalanceSnapshot,
    ChartTraceResponse,
    DashboardResponse,
    DesktopAgentRecord,
    DesktopAgentStatus,
    EntityType,
    ForecastInput,
    ForecastScenario,
    ImportBatch,
    ObligationFrequency,
    ParsedImportBundle,
    RecurringObligation,
    ReportRequest,
    ScenarioKind,
    SourceConnectionRecord,
    SourceConnectionStatus,
    SourceType,
    utc_now,
)
from cashflow_os.forecast.engine import build_forecast_run, build_standard_scenario_runs
from cashflow_os.ingestion.service import parse_import
from cashflow_os.ingestion.zoho_client import (
    ZohoApiError,
    ZohoConfigurationError,
    build_zoho_authorization_url,
    choose_default_organization,
    exchange_zoho_authorization_code,
    fetch_zoho_import_payload,
    list_zoho_organizations,
    refresh_zoho_access_token,
    token_is_expired,
)
from cashflow_os.reports.builder import build_report_pack
from cashflow_os.reports.exporters import export_excel, export_pdf
from cashflow_os.reports.traces import resolve_report_chart_trace


logging.basicConfig(level=os.getenv("CASHFLOW_LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger("cashflow_os.api")

STORE: Union[InMemoryStore, PostgresRepository] = InMemoryStore()


@asynccontextmanager
async def lifespan(application: FastAPI):
    global STORE
    database_url = get_database_url()
    if database_url:
        LOGGER.info("DATABASE_URL detected — initializing PostgreSQL backend.")
        init_engine()
        STORE = PostgresRepository()
        STORE.seed_demo()
        LOGGER.info("PostgreSQL repository ready.")
    else:
        LOGGER.info("No DATABASE_URL — using InMemoryStore (local dev mode).")
        STORE = InMemoryStore()
    yield
    if is_postgres_available():
        dispose_engine()
        LOGGER.info("PostgreSQL connections closed.")


app = FastAPI(title="India Cashflow OS API", version="0.2.0", lifespan=lifespan)
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CASHFLOW_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    LOGGER.info("%s %s -> %s in %sms", request.method, request.url.path, response.status_code, duration_ms)
    return response


def _build_demo_bundle() -> ParsedImportBundle:
    demo_input = next(iter(STORE.forecast_inputs.values()))
    counterparties = list(demo_input.counterparties)
    events = list(demo_input.events)
    obligations = list(demo_input.obligations)
    return ParsedImportBundle(
        import_batch=ImportBatch(
            org_id=demo_input.profile.org_id,
            source_type=SourceType.DEMO,
            filename="demo-seed",
            event_count=len(events),
            counterparty_count=len(counterparties),
            obligation_count=len(obligations),
        ),
        bank_balance=demo_input.opening_balance,
        inventory_snapshot=demo_input.inventory_snapshot,
        counterparties=counterparties,
        events=events,
        obligations=obligations,
    )


def _select_forecast_run(
    forecast_run_id: Optional[str] = None,
    org_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
):
    if forecast_run_id:
        return STORE.forecast_runs.get(forecast_run_id)

    runs = list(STORE.forecast_runs.values())
    if org_id:
        runs = [run for run in runs if run.org_id == org_id]
    if scenario_id:
        runs = [run for run in runs if run.scenario.scenario_id == scenario_id]
    if not runs:
        return None
    return max(runs, key=lambda run: _normalize_generated_at(run.generated_at))


def _normalize_generated_at(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _compute_import_checksum(
    source_type: SourceType,
    *,
    file_bytes: Optional[bytes] = None,
    file_text: Optional[str] = None,
    payload: Optional[dict] = None,
    source_hint: Optional[str] = None,
) -> str:
    digest = hashlib.sha256()
    digest.update(source_type.value.encode("utf-8"))
    digest.update(b"\0")
    digest.update((source_hint or "").encode("utf-8"))
    digest.update(b"\0")
    if file_bytes is not None:
        digest.update(file_bytes)
    else:
        digest.update((file_text or "").encode("utf-8"))
        digest.update(json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8"))
    return digest.hexdigest()


def _build_confirmed_scenario(payload: ConfirmImportPayload) -> ForecastScenario:
    scenario_payload = payload.scenario
    if scenario_payload is None:
        return ForecastScenario(
            name="Base Case",
            kind=ScenarioKind.BASE,
            description="Confirmed after mapping review",
            minimum_cash_buffer_minor_units=payload.minimum_cash_buffer_minor_units,
        )

    scenario_name = scenario_payload.name.strip() or "Base Case"
    has_custom_adjustments = any(
        (
            scenario_payload.inflow_delay_days,
            scenario_payload.outflow_delay_days,
            scenario_payload.inflow_scalar_bps != 10000,
            scenario_payload.outflow_scalar_bps != 10000,
            scenario_payload.opening_cash_adjustment_minor_units,
        )
    )
    return ForecastScenario(
        name=scenario_name,
        kind=ScenarioKind.CUSTOM if has_custom_adjustments or scenario_name != "Base Case" else ScenarioKind.BASE,
        description=scenario_payload.description or "Confirmed after mapping review",
        inflow_delay_days=scenario_payload.inflow_delay_days,
        outflow_delay_days=scenario_payload.outflow_delay_days,
        inflow_scalar_bps=scenario_payload.inflow_scalar_bps,
        outflow_scalar_bps=scenario_payload.outflow_scalar_bps,
        opening_cash_adjustment_minor_units=scenario_payload.opening_cash_adjustment_minor_units,
        minimum_cash_buffer_minor_units=payload.minimum_cash_buffer_minor_units,
    )


def _build_manual_obligations(org_id: str, payload: list[ObligationSetupPayload]) -> list[RecurringObligation]:
    obligations: list[RecurringObligation] = []
    for entry in payload:
        obligation_type = EntityType(entry.obligation_type) if entry.obligation_type in EntityType._value2member_map_ else EntityType.OTHER
        frequency = (
            ObligationFrequency(entry.frequency)
            if entry.frequency in ObligationFrequency._value2member_map_
            else ObligationFrequency.MONTHLY
        )
        obligations.append(
            RecurringObligation(
                org_id=org_id,
                name=entry.name.strip() or obligation_type.value.title(),
                obligation_type=obligation_type,
                frequency=frequency,
                amount_minor_units=entry.amount_minor_units,
                due_day=entry.due_day,
                start_date=entry.start_date,
                end_date=entry.end_date,
                notes=entry.notes,
            )
        )
    return obligations


def _resolve_zoho_redirect_uri(explicit_redirect_uri: Optional[str], metadata: Optional[dict] = None) -> Optional[str]:
    return explicit_redirect_uri or (metadata or {}).get("redirect_uri") or os.getenv("ZOHO_REDIRECT_URI")


def _configured_for_live_zoho(redirect_uri: Optional[str]) -> bool:
    return bool(os.getenv("ZOHO_CLIENT_ID") and os.getenv("ZOHO_CLIENT_SECRET") and redirect_uri)


def _update_desktop_agent_activity(
    *,
    desktop_agent_id: Optional[str],
    org_id: str,
    watched_path: Optional[str] = None,
    last_uploaded_at: Optional[datetime] = None,
    last_upload_filename: Optional[str] = None,
    last_upload_batch_id: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    if not desktop_agent_id:
        return

    agent = STORE.desktop_agents.get(desktop_agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Desktop agent not found")
    if agent.org_id != org_id:
        raise HTTPException(status_code=403, detail="Desktop agent does not belong to this organization")

    agent.status = DesktopAgentStatus.ONLINE
    agent.last_seen_at = utc_now()
    if watched_path:
        agent.watched_path = watched_path
    if last_uploaded_at is not None:
        agent.last_uploaded_at = last_uploaded_at
    if last_upload_filename:
        agent.last_upload_filename = last_upload_filename
    if last_upload_batch_id:
        agent.last_upload_batch_id = last_upload_batch_id
    if message is not None:
        agent.message = message
    STORE.upsert_desktop_agent(agent)


@app.get("/health")
def health() -> dict:
    backend = "postgresql" if is_postgres_available() else "in_memory"
    db_ok = db_health_check() if is_postgres_available() else True
    return {"status": "ok" if db_ok else "degraded", "backend": backend, "database_connected": db_ok}


@app.get("/v1/auth/session")
def auth_session(principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant", "viewer"))):
    return principal


@app.post("/v1/imports", response_model=ParsedImportBundle)
async def create_import(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    org_id: Optional[str] = Form(default=None),
    source_type: Optional[str] = Form(default=None),
    source_hint: Optional[str] = Form(default=None),
    desktop_agent_id: Optional[str] = Form(default=None),
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant")),
):
    if file is not None:
        payload_org_id = org_id or principal.org_id
        ensure_org_access(principal, payload_org_id)
        resolved_source_type = SourceType(source_type or "manual")
        file_bytes = await file.read()
        checksum = _compute_import_checksum(
            resolved_source_type,
            file_bytes=file_bytes,
            source_hint=source_hint,
        )
        existing_bundle = STORE.find_import_by_checksum(payload_org_id, resolved_source_type, checksum)
        if existing_bundle is not None:
            _update_desktop_agent_activity(
                desktop_agent_id=desktop_agent_id,
                org_id=payload_org_id,
                last_uploaded_at=utc_now(),
                last_upload_filename=file.filename,
                last_upload_batch_id=existing_bundle.import_batch.import_batch_id,
                message="Desktop sync bridge uploaded a duplicate file and the API reused the existing import batch.",
            )
            return existing_bundle
        bundle = parse_import(
            org_id=payload_org_id,
            source_type=resolved_source_type,
            filename=file.filename,
            file_bytes=file_bytes,
            source_hint=source_hint,
        )
        bundle.import_batch.checksum = checksum
    else:
        payload = ImportCreatePayload.model_validate(await request.json())
        payload_org_id = payload.org_id or principal.org_id
        ensure_org_access(principal, payload_org_id)
        if payload.use_demo:
            bundle = _build_demo_bundle()
        else:
            resolved_source_type = SourceType(payload.source_type)
            checksum = _compute_import_checksum(
                resolved_source_type,
                file_text=payload.text_content,
                payload=payload.payload,
                source_hint=payload.source_hint,
            )
            existing_bundle = STORE.find_import_by_checksum(payload_org_id, resolved_source_type, checksum)
            if existing_bundle is not None:
                return existing_bundle
            bundle = parse_import(
                org_id=payload_org_id,
                source_type=resolved_source_type,
                filename=payload.filename,
                file_text=payload.text_content,
                payload=payload.payload,
                source_hint=payload.source_hint,
            )
            bundle.import_batch.checksum = checksum

    ensure_org_access(principal, bundle.import_batch.org_id)
    STORE.upsert_import(bundle)
    _update_desktop_agent_activity(
        desktop_agent_id=desktop_agent_id,
        org_id=bundle.import_batch.org_id,
        last_uploaded_at=utc_now(),
        last_upload_filename=bundle.import_batch.filename,
        last_upload_batch_id=bundle.import_batch.import_batch_id,
        message="Desktop sync bridge uploaded the latest file successfully.",
    )
    return bundle


@app.get("/v1/imports/{import_batch_id}", response_model=ParsedImportBundle)
def get_import(
    import_batch_id: str,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant", "viewer")),
) -> ParsedImportBundle:
    bundle = STORE.imports.get(import_batch_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Import batch not found")
    ensure_org_access(principal, bundle.import_batch.org_id)
    return bundle


@app.post("/v1/imports/{import_batch_id}/confirm-mapping", response_model=ForecastInput)
def confirm_mapping(
    import_batch_id: str,
    payload: ConfirmImportPayload,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant")),
) -> ForecastInput:
    bundle = STORE.imports.get(import_batch_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Import batch not found")
    ensure_org_access(principal, bundle.import_batch.org_id)

    opening_balance_minor_units = payload.opening_balance_minor_units
    if opening_balance_minor_units is None:
        opening_balance_minor_units = bundle.bank_balance.balance_minor_units if bundle.bank_balance else 0

    scenario = _build_confirmed_scenario(payload)
    obligations = [*bundle.obligations, *_build_manual_obligations(bundle.import_batch.org_id, payload.obligations)]
    forecast_input = ForecastInput(
        profile={
            "org_id": bundle.import_batch.org_id,
            "company_name": payload.company_name,
            "industry": payload.industry,
        },
        as_of_date=payload.as_of_date,
        opening_balance=BankBalanceSnapshot(
            org_id=bundle.import_batch.org_id,
            as_of_date=payload.as_of_date,
            balance_minor_units=opening_balance_minor_units,
        ),
        inventory_snapshot=bundle.inventory_snapshot,
        counterparties=bundle.counterparties,
        events=bundle.events,
        obligations=obligations,
        scenario=scenario,
    )
    STORE.upsert_forecast_input(import_batch_id, forecast_input)
    return forecast_input


@app.post("/v1/obligations", response_model=RecurringObligation)
def create_obligation(
    obligation: RecurringObligation,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager")),
) -> RecurringObligation:
    ensure_org_access(principal, obligation.org_id)
    STORE.add_obligation(obligation)
    return obligation


@app.post("/v1/sources/zoho/connect", response_model=SourceConnectionRecord)
def connect_zoho(
    request: ZohoConnectRequest,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager")),
) -> SourceConnectionRecord:
    ensure_org_access(principal, request.org_id)
    redirect_uri = _resolve_zoho_redirect_uri(request.redirect_uri)
    connection = SourceConnectionRecord(
        org_id=request.org_id,
        source_type=SourceType.ZOHO,
        client_name=request.client_name,
        status=SourceConnectionStatus.PENDING,
        capabilities=["json_payload_ingestion"],
        metadata={"redirect_uri": redirect_uri} if redirect_uri else {},
    )
    if _configured_for_live_zoho(redirect_uri):
        oauth_state = secrets.token_urlsafe(32)
        connection.auth_url = build_zoho_authorization_url(oauth_state, redirect_uri or "")
        connection.capabilities.extend(["live_oauth", "remote_sync"])
        connection.message = "Zoho authorization is ready. Redirect the user to the returned auth_url to complete the connection."
    else:
        connection.capabilities.append("oauth_configuration_required")
        connection.message = "Zoho payload ingestion is ready. Set ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, and ZOHO_REDIRECT_URI to enable live OAuth."
    STORE.upsert_source_connection(connection)
    if _configured_for_live_zoho(redirect_uri):
        STORE.register_oauth_state(connection.connection_id, oauth_state)
    return connection


@app.post("/v1/sources/zoho/exchange", response_model=SourceConnectionRecord)
def exchange_zoho_connection(
    request: ZohoExchangeRequest,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager")),
) -> SourceConnectionRecord:
    connection = STORE.source_connections.get(request.connection_id)
    if connection is None or connection.source_type != SourceType.ZOHO:
        raise HTTPException(status_code=404, detail="Zoho connection not found")
    ensure_org_access(principal, connection.org_id)

    resolved_connection_id = STORE.consume_oauth_state(request.state)
    if resolved_connection_id != connection.connection_id:
        raise HTTPException(status_code=400, detail="Zoho OAuth state is invalid or expired.")

    redirect_uri = _resolve_zoho_redirect_uri(None, connection.metadata)
    if not redirect_uri:
        raise HTTPException(status_code=503, detail="ZOHO_REDIRECT_URI is required to complete OAuth.")

    try:
        token_payload = exchange_zoho_authorization_code(
            request.code,
            redirect_uri,
            accounts_server=request.accounts_server,
        )
        organizations = list_zoho_organizations(
            token_payload["access_token"],
            api_domain=token_payload.get("api_domain"),
        )
    except (ZohoApiError, ZohoConfigurationError) as exc:
        connection.status = SourceConnectionStatus.FAILED
        connection.message = str(exc)
        STORE.upsert_source_connection(connection)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    selected_org = choose_default_organization(organizations)
    connection.status = SourceConnectionStatus.ACTIVE
    connection.external_organization_id = selected_org.get("organization_id") if selected_org else None
    connection.external_organization_name = selected_org.get("name") if selected_org else None
    connection.capabilities = sorted(set(connection.capabilities + ["live_oauth", "remote_sync"]))
    connection.message = "Zoho Books authorization completed. You can sync invoices and bills into the import flow."
    connection.auth_url = None
    connection.metadata = {
        **connection.metadata,
        "api_domain": token_payload.get("api_domain"),
        "accounts_server": token_payload.get("accounts_server"),
        "organizations": [
            {
                "organization_id": org.get("organization_id"),
                "name": org.get("name"),
                "is_default_org": bool(org.get("is_default_org")),
            }
            for org in organizations
        ],
    }
    STORE.upsert_source_token(connection.connection_id, token_payload)
    STORE.upsert_source_connection(connection)
    return connection


@app.post("/v1/sources/zoho/{connection_id}/sync", response_model=ParsedImportBundle)
def sync_zoho_connection(
    connection_id: str,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant")),
) -> ParsedImportBundle:
    connection = STORE.source_connections.get(connection_id)
    if connection is None or connection.source_type != SourceType.ZOHO:
        raise HTTPException(status_code=404, detail="Zoho connection not found")
    ensure_org_access(principal, connection.org_id)

    token_payload = STORE.get_source_token(connection_id)
    if token_payload is None:
        raise HTTPException(status_code=409, detail="Zoho connection has not completed OAuth.")

    try:
        if token_is_expired(token_payload):
            refresh_token = token_payload.get("refresh_token")
            if not refresh_token:
                raise ZohoApiError("Zoho refresh token is missing. Reconnect the source and try again.")
            refreshed_payload = refresh_zoho_access_token(
                refresh_token,
                accounts_server=token_payload.get("accounts_server"),
            )
            token_payload = {**token_payload, **refreshed_payload}
            STORE.upsert_source_token(connection_id, token_payload)

        selected_organization_id = connection.external_organization_id
        selected_organization_name = connection.external_organization_name
        if not selected_organization_id:
            organizations = list_zoho_organizations(
                token_payload["access_token"],
                api_domain=token_payload.get("api_domain"),
            )
            selected_org = choose_default_organization(organizations)
            if selected_org is None:
                raise ZohoApiError("No Zoho Books organizations are available for this account.")
            selected_organization_id = str(selected_org.get("organization_id"))
            selected_organization_name = selected_org.get("name")

        zoho_payload = fetch_zoho_import_payload(
            token_payload["access_token"],
            api_domain=token_payload.get("api_domain") or connection.metadata.get("api_domain"),
            organization_id=selected_organization_id,
        )
    except (ZohoApiError, ZohoConfigurationError) as exc:
        connection.status = SourceConnectionStatus.FAILED
        connection.message = str(exc)
        STORE.upsert_source_connection(connection)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    checksum = _compute_import_checksum(
        SourceType.ZOHO,
        payload=zoho_payload,
        source_hint=selected_organization_id,
    )
    existing_bundle = STORE.find_import_by_checksum(connection.org_id, SourceType.ZOHO, checksum)
    if existing_bundle is not None:
        return existing_bundle

    bundle = parse_import(
        org_id=connection.org_id,
        source_type=SourceType.ZOHO,
        filename="zoho-books-{organization_id}.json".format(organization_id=selected_organization_id),
        payload=zoho_payload,
        source_hint=selected_organization_id,
    )
    bundle.import_batch.checksum = checksum
    STORE.upsert_import(bundle)

    connection.status = SourceConnectionStatus.ACTIVE
    connection.external_organization_id = selected_organization_id
    connection.external_organization_name = selected_organization_name
    connection.last_synced_at = utc_now()
    connection.message = "Zoho Books sync completed. The latest invoices and bills are ready in the import flow."
    connection.metadata = {
        **connection.metadata,
        "api_domain": token_payload.get("api_domain"),
        "last_sync_import_batch_id": bundle.import_batch.import_batch_id,
        "last_sync_event_count": bundle.import_batch.event_count,
    }
    STORE.upsert_source_connection(connection)
    return bundle


@app.post("/v1/desktop-agents/register", response_model=DesktopAgentRecord)
def register_desktop_agent(
    request: DesktopAgentRegistrationRequest,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager")),
) -> DesktopAgentRecord:
    ensure_org_access(principal, request.org_id)
    agent = DesktopAgentRecord(
        org_id=request.org_id,
        machine_name=request.machine_name,
        last_seen_at=utc_now(),
        capabilities=["manual_upload_ready", "folder_watch_ready", "local_tally_bridge_ready"],
        message="Desktop registration completed. The local sync bridge can now watch a folder and upload supported files through the API.",
    )
    STORE.upsert_desktop_agent(agent)
    return agent


@app.post("/v1/desktop-agents/{agent_id}/heartbeat", response_model=DesktopAgentRecord)
def heartbeat_desktop_agent(
    agent_id: str,
    request: DesktopAgentHeartbeatRequest,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager")),
) -> DesktopAgentRecord:
    agent = STORE.desktop_agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Desktop agent not found")
    ensure_org_access(principal, agent.org_id)
    agent.status = request.status
    agent.last_seen_at = utc_now()
    if request.watched_path is not None:
        agent.watched_path = request.watched_path
    if request.message is not None:
        agent.message = request.message
    STORE.upsert_desktop_agent(agent)
    return agent


@app.post("/v1/scenarios", response_model=ForecastScenario)
def create_scenario(
    scenario: ForecastScenario,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant")),
) -> ForecastScenario:
    ensure_org_access(principal, principal.org_id)
    STORE.upsert_scenario(scenario)
    return scenario


@app.post("/v1/forecast-runs")
def create_forecast_run(
    forecast_input: ForecastInput,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant")),
):
    ensure_org_access(principal, forecast_input.profile.org_id)
    run = build_forecast_run(forecast_input)
    STORE.upsert_forecast_run(run, forecast_input=forecast_input)
    return run


@app.get("/v1/forecast-runs/{forecast_run_id}")
def get_forecast_run(
    forecast_run_id: str,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant", "viewer")),
):
    run = STORE.forecast_runs.get(forecast_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    ensure_org_access(principal, run.org_id)
    return run


@app.get("/v1/dashboards/cash", response_model=DashboardResponse)
def get_cash_dashboard(
    forecast_run_id: Optional[str] = Query(default=None),
    org_id: Optional[str] = Query(default=None),
    scenario_id: Optional[str] = Query(default=None),
    demo: bool = Query(default=False),
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant", "viewer")),
):
    effective_org_id = org_id or principal.org_id
    ensure_org_access(principal, effective_org_id)
    run = _select_forecast_run(
        forecast_run_id=forecast_run_id,
        org_id=None if forecast_run_id else effective_org_id,
        scenario_id=scenario_id,
    )
    if run is None and demo:
        run = _select_forecast_run(org_id=effective_org_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    ensure_org_access(principal, run.org_id)
    forecast_input = STORE.forecast_inputs.get(run.forecast_run_id)
    comparison_runs = build_standard_scenario_runs(forecast_input) if forecast_input is not None else None
    report_pack = build_report_pack(run, comparison_runs=comparison_runs)
    STORE.upsert_report(report_pack)
    return DashboardResponse(forecast_run=run, report_pack=report_pack)


@app.post("/v1/reports")
def create_report(
    request: ReportRequest,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant")),
):
    run = STORE.forecast_runs.get(request.forecast_run_id)
    forecast_input = STORE.forecast_inputs.get(request.forecast_run_id)
    if run is None or forecast_input is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    ensure_org_access(principal, run.org_id)
    comparison_runs = build_standard_scenario_runs(forecast_input) if request.include_scenarios else None
    report_pack = build_report_pack(run, comparison_runs=comparison_runs)
    STORE.upsert_report(report_pack)
    STORE.cache_report_file(report_pack.report_id, "pdf", export_pdf(run, report_pack))
    STORE.cache_report_file(report_pack.report_id, "xlsx", export_excel(run, report_pack))
    return report_pack


@app.get("/v1/reports/{report_id}/download")
def download_report(
    report_id: str,
    format: str = Query(pattern="^(pdf|xlsx)$"),
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant", "viewer")),
):
    report_pack = STORE.reports.get(report_id)
    if report_pack is None:
        raise HTTPException(status_code=404, detail="Report export not found")
    run = STORE.forecast_runs.get(report_pack.forecast_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    ensure_org_access(principal, run.org_id)
    content = STORE.read_report_file(report_id, format)
    if content is None:
        content = export_pdf(run, report_pack) if format == "pdf" else export_excel(run, report_pack)
        STORE.cache_report_file(report_id, format, content)
    media_type = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(content=content, media_type=media_type)


@app.get("/v1/reports/{report_id}/charts/{chart_id}/trace", response_model=ChartTraceResponse)
def get_report_chart_trace(
    report_id: str,
    chart_id: str,
    point_key: Optional[str] = Query(default=None),
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant", "viewer")),
):
    report_pack = STORE.reports.get(report_id)
    if report_pack is None:
        raise HTTPException(status_code=404, detail="Report pack not found")
    run = STORE.forecast_runs.get(report_pack.forecast_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    ensure_org_access(principal, run.org_id)
    try:
        return resolve_report_chart_trace(report_pack, run, chart_id, point_key=point_key)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/audit/trace")
def get_audit_trace(
    forecast_run_id: str,
    event_id: Optional[str] = None,
    principal: AuthPrincipal = Depends(require_roles("owner", "finance_manager", "accountant", "viewer")),
):
    run = STORE.forecast_runs.get(forecast_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    ensure_org_access(principal, run.org_id)
    if event_id:
        return [trace for trace in run.audit_trace if trace.event_id == event_id]
    return run.audit_trace
