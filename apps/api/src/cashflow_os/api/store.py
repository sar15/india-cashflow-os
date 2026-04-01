import json
import os
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Dict, List, Optional, Type, TypeVar

from cashflow_os.api.blob_storage import (
    is_blob_storage_enabled,
    read_private_bytes,
    report_blob_path,
    state_blob_path,
    write_private_bytes,
)
from cashflow_os.domain.models import (
    BankBalanceSnapshot,
    CanonicalCashEvent,
    Counterparty,
    DesktopAgentRecord,
    EntityType,
    EventType,
    EventStatus,
    ForecastInput,
    ForecastRun,
    ForecastScenario,
    ImportBatch,
    InventorySnapshot,
    OrganizationProfile,
    ParsedImportBundle,
    RecurringObligation,
    RelationshipType,
    ReportPack,
    ScenarioKind,
    SourceType,
    SourceConnectionRecord,
)
from cashflow_os.forecast.engine import build_forecast_run
from cashflow_os.reports.builder import build_report_pack
from cashflow_os.utils.money import to_minor_units


STATE_FILE_VERSION = 1
ModelT = TypeVar("ModelT")


def _default_state_path() -> Path:
    configured = os.getenv("CASHFLOW_STATE_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[5] / "data" / "cashflow-os-state.json"


def _default_report_storage_path() -> Path:
    configured = os.getenv("CASHFLOW_REPORT_STORAGE_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[5] / "data" / "report-files"


def _dump_model_map(records: Dict[str, ModelT]) -> Dict[str, dict]:
    return {key: record.model_dump(mode="json") for key, record in records.items()}


def _load_model_map(payload: Dict[str, dict], model_type: Type[ModelT]) -> Dict[str, ModelT]:
    return {key: model_type.model_validate(value) for key, value in payload.items()}


def _dump_model_list_map(records: Dict[str, List[ModelT]]) -> Dict[str, List[dict]]:
    return {key: [record.model_dump(mode="json") for record in values] for key, values in records.items()}


def _load_model_list_map(payload: Dict[str, List[dict]], model_type: Type[ModelT]) -> Dict[str, List[ModelT]]:
    return {key: [model_type.model_validate(value) for value in values] for key, values in payload.items()}


class InMemoryStore:
    def __init__(self, state_path: Optional[Path] = None, report_storage_path: Optional[Path] = None) -> None:
        self.state_path = Path(state_path) if state_path else _default_state_path()
        self.report_storage_path = Path(report_storage_path) if report_storage_path else _default_report_storage_path()
        self.use_blob_storage = is_blob_storage_enabled()
        self._lock = Lock()
        self.imports: Dict[str, ParsedImportBundle] = {}
        self.import_checksums: Dict[str, str] = {}
        self.forecast_inputs: Dict[str, ForecastInput] = {}
        self.forecast_runs: Dict[str, ForecastRun] = {}
        self.reports: Dict[str, ReportPack] = {}
        self.report_files: Dict[str, Dict[str, bytes]] = {}
        self.obligations: Dict[str, List[RecurringObligation]] = {}
        self.scenarios: Dict[str, ForecastScenario] = {}
        self.source_connections: Dict[str, SourceConnectionRecord] = {}
        self.desktop_agents: Dict[str, DesktopAgentRecord] = {}
        self.source_tokens: Dict[str, dict] = {}
        self.oauth_states: Dict[str, str] = {}
        self._load_state()
        if not self.forecast_runs:
            self.seed_demo()

    def _load_state(self) -> None:
        if self.use_blob_storage:
            raw_payload = read_private_bytes(state_blob_path())
            if raw_payload is None:
                return
            try:
                payload = json.loads(raw_payload.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError("Blob state payload is not valid JSON.") from exc
        else:
            if not self.state_path.exists():
                return

            try:
                payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "State file at {path} is not valid JSON.".format(path=self.state_path)
                ) from exc

        if payload.get("version") != STATE_FILE_VERSION:
            return

        self.imports = _load_model_map(payload.get("imports", {}), ParsedImportBundle)
        self.import_checksums = payload.get("import_checksums", {})
        self.forecast_inputs = _load_model_map(payload.get("forecast_inputs", {}), ForecastInput)
        self.forecast_runs = _load_model_map(payload.get("forecast_runs", {}), ForecastRun)
        self.reports = _load_model_map(payload.get("reports", {}), ReportPack)
        self.obligations = _load_model_list_map(payload.get("obligations", {}), RecurringObligation)
        self.scenarios = _load_model_map(payload.get("scenarios", {}), ForecastScenario)
        self.source_connections = _load_model_map(payload.get("source_connections", {}), SourceConnectionRecord)
        self.desktop_agents = _load_model_map(payload.get("desktop_agents", {}), DesktopAgentRecord)
        self.source_tokens = payload.get("source_tokens", {})
        self.oauth_states = payload.get("oauth_states", {})

    def _save_state(self) -> None:
        state_payload = {
            "version": STATE_FILE_VERSION,
            "imports": _dump_model_map(self.imports),
            "import_checksums": self.import_checksums,
            "forecast_inputs": _dump_model_map(self.forecast_inputs),
            "forecast_runs": _dump_model_map(self.forecast_runs),
            "reports": _dump_model_map(self.reports),
            "obligations": _dump_model_list_map(self.obligations),
            "scenarios": _dump_model_map(self.scenarios),
            "source_connections": _dump_model_map(self.source_connections),
            "desktop_agents": _dump_model_map(self.desktop_agents),
            "source_tokens": self.source_tokens,
            "oauth_states": self.oauth_states,
        }

        with self._lock:
            if self.use_blob_storage:
                write_private_bytes(
                    state_blob_path(),
                    json.dumps(state_payload, indent=2, sort_keys=True).encode("utf-8"),
                    content_type="application/json",
                )
                return

            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile("w", delete=False, dir=self.state_path.parent, encoding="utf-8") as temporary_file:
                json.dump(state_payload, temporary_file, indent=2, sort_keys=True)
                temporary_path = Path(temporary_file.name)
            temporary_path.replace(self.state_path)

    def seed_demo(self) -> None:
        if self.forecast_runs:
            return
        demo_input = build_demo_forecast_input()
        demo_run = build_forecast_run(demo_input)
        demo_report = build_report_pack(demo_run)
        self.forecast_inputs[demo_run.forecast_run_id] = demo_input
        self.forecast_runs[demo_run.forecast_run_id] = demo_run
        self.reports[demo_report.report_id] = demo_report
        self._save_state()

    def upsert_import(self, bundle: ParsedImportBundle) -> None:
        self.imports[bundle.import_batch.import_batch_id] = bundle
        if bundle.import_batch.checksum:
            self.import_checksums[self._import_checksum_key(bundle.import_batch.org_id, bundle.import_batch.source_type, bundle.import_batch.checksum)] = (
                bundle.import_batch.import_batch_id
            )
        self._save_state()

    def upsert_forecast_input(self, key: str, forecast_input: ForecastInput) -> None:
        self.forecast_inputs[key] = forecast_input
        self._save_state()

    def add_obligation(self, obligation: RecurringObligation) -> None:
        self.obligations.setdefault(obligation.org_id, []).append(obligation)
        self._save_state()

    def upsert_source_connection(self, connection: SourceConnectionRecord) -> None:
        self.source_connections[connection.connection_id] = connection
        self._save_state()

    def register_oauth_state(self, connection_id: str, state: str) -> None:
        self.oauth_states[state] = connection_id
        self._save_state()

    def consume_oauth_state(self, state: str) -> Optional[str]:
        connection_id = self.oauth_states.pop(state, None)
        self._save_state()
        return connection_id

    def upsert_source_token(self, connection_id: str, token_payload: dict) -> None:
        self.source_tokens[connection_id] = token_payload
        self._save_state()

    def get_source_token(self, connection_id: str) -> Optional[dict]:
        token_payload = self.source_tokens.get(connection_id)
        if token_payload is None:
            return None
        return dict(token_payload)

    def upsert_desktop_agent(self, agent: DesktopAgentRecord) -> None:
        self.desktop_agents[agent.agent_id] = agent
        self._save_state()

    def upsert_scenario(self, scenario: ForecastScenario) -> None:
        self.scenarios[scenario.scenario_id] = scenario
        self._save_state()

    def upsert_forecast_run(self, run: ForecastRun, forecast_input: Optional[ForecastInput] = None) -> None:
        if forecast_input is not None:
            self.forecast_inputs[run.forecast_run_id] = forecast_input
        self.forecast_runs[run.forecast_run_id] = run
        self._save_state()

    def upsert_report(self, report: ReportPack) -> None:
        self.reports[report.report_id] = report
        self._save_state()

    def cache_report_file(self, report_id: str, file_format: str, content: bytes) -> None:
        self.report_files.setdefault(report_id, {})[file_format] = content
        if self.use_blob_storage:
            content_type = "application/pdf" if file_format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            write_private_bytes(report_blob_path(report_id, file_format), content, content_type=content_type)
            return

        self.report_storage_path.mkdir(parents=True, exist_ok=True)
        report_path = self.report_storage_path / "{report_id}.{file_format}".format(
            report_id=report_id,
            file_format=file_format,
        )
        report_path.write_bytes(content)

    def read_report_file(self, report_id: str, file_format: str) -> Optional[bytes]:
        in_memory = self.report_files.get(report_id, {}).get(file_format)
        if in_memory is not None:
            return in_memory

        if self.use_blob_storage:
            content = read_private_bytes(report_blob_path(report_id, file_format))
            if content is None:
                return None
            self.report_files.setdefault(report_id, {})[file_format] = content
            return content

        report_path = self.report_storage_path / "{report_id}.{file_format}".format(
            report_id=report_id,
            file_format=file_format,
        )
        if not report_path.exists():
            return None
        content = report_path.read_bytes()
        self.report_files.setdefault(report_id, {})[file_format] = content
        return content

    def find_import_by_checksum(self, org_id: str, source_type: SourceType, checksum: Optional[str]) -> Optional[ParsedImportBundle]:
        if not checksum:
            return None
        import_batch_id = self.import_checksums.get(self._import_checksum_key(org_id, source_type, checksum))
        if import_batch_id is None:
            return None
        return self.imports.get(import_batch_id)

    @staticmethod
    def _import_checksum_key(org_id: str, source_type: SourceType, checksum: str) -> str:
        return "{org_id}:{source_type}:{checksum}".format(org_id=org_id, source_type=source_type.value, checksum=checksum)


def build_demo_forecast_input() -> ForecastInput:
    org_id = "demo-org"
    as_of = date(2026, 4, 1)
    profile = OrganizationProfile(
        org_id=org_id,
        company_name="Shakti Components Pvt Ltd",
        industry="Manufacturing",
    )
    counterparties = [
        Counterparty(entity_name="Sharma Retail", relationship_type=RelationshipType.CUSTOMER, behavioral_delay_days=4, collection_confidence=0.82),
        Counterparty(entity_name="Delta Foods", relationship_type=RelationshipType.CUSTOMER, behavioral_delay_days=12, collection_confidence=0.58),
        Counterparty(entity_name="Apex Steel", relationship_type=RelationshipType.VENDOR, is_msme_registered=True),
        Counterparty(entity_name="Universal Packaging", relationship_type=RelationshipType.VENDOR),
    ]
    customer_map = {counterparty.entity_name: counterparty for counterparty in counterparties}
    events = [
        CanonicalCashEvent(
            org_id=org_id,
            source_id="demo.seed",
            import_batch_id="demo-batch",
            event_type=EventType.INFLOW,
            entity_type=EntityType.INVOICE,
            counterparty_id=customer_map["Sharma Retail"].counterparty_id,
            counterparty_name="Sharma Retail",
            document_number="INV-2026-041",
            document_date=date(2026, 3, 25),
            due_date=date(2026, 4, 8),
            gross_minor_units=to_minor_units(1200000),
            net_minor_units=to_minor_units(1200000),
            status=EventStatus.OPEN,
        ),
        CanonicalCashEvent(
            org_id=org_id,
            source_id="demo.seed",
            import_batch_id="demo-batch",
            event_type=EventType.INFLOW,
            entity_type=EntityType.INVOICE,
            counterparty_id=customer_map["Delta Foods"].counterparty_id,
            counterparty_name="Delta Foods",
            document_number="INV-2026-052",
            document_date=date(2026, 3, 28),
            due_date=date(2026, 4, 18),
            gross_minor_units=to_minor_units(850000),
            tds_minor_units=to_minor_units(8500),
            net_minor_units=to_minor_units(841500),
            status=EventStatus.OPEN,
        ),
        CanonicalCashEvent(
            org_id=org_id,
            source_id="demo.seed",
            import_batch_id="demo-batch",
            event_type=EventType.OUTFLOW,
            entity_type=EntityType.BILL,
            counterparty_id=customer_map["Apex Steel"].counterparty_id,
            counterparty_name="Apex Steel",
            document_number="BILL-STEEL-019",
            document_date=date(2026, 3, 1),
            due_date=date(2026, 4, 20),
            gross_minor_units=to_minor_units(900000),
            net_minor_units=to_minor_units(900000),
            status=EventStatus.OPEN,
        ),
        CanonicalCashEvent(
            org_id=org_id,
            source_id="demo.seed",
            import_batch_id="demo-batch",
            event_type=EventType.OUTFLOW,
            entity_type=EntityType.BILL,
            counterparty_id=customer_map["Universal Packaging"].counterparty_id,
            counterparty_name="Universal Packaging",
            document_number="BILL-PACK-028",
            document_date=date(2026, 3, 30),
            due_date=date(2026, 4, 14),
            gross_minor_units=to_minor_units(475000),
            net_minor_units=to_minor_units(475000),
            status=EventStatus.OPEN,
        ),
        CanonicalCashEvent(
            org_id=org_id,
            source_id="demo.seed",
            import_batch_id="demo-batch",
            event_type=EventType.OUTFLOW,
            entity_type=EntityType.MANUAL,
            document_number="UTILITY-APR",
            document_date=date(2026, 4, 9),
            due_date=date(2026, 4, 9),
            gross_minor_units=to_minor_units(85000),
            net_minor_units=to_minor_units(85000),
            status=EventStatus.PLANNED,
        ),
    ]
    obligations = [
        RecurringObligation(org_id=org_id, name="Payroll", obligation_type=EntityType.PAYROLL, amount_minor_units=to_minor_units(360000), start_date=as_of),
        RecurringObligation(org_id=org_id, name="GST", obligation_type=EntityType.GST, amount_minor_units=to_minor_units(220000), start_date=as_of),
        RecurringObligation(org_id=org_id, name="TDS", obligation_type=EntityType.TDS, amount_minor_units=to_minor_units(65000), start_date=as_of),
        RecurringObligation(org_id=org_id, name="EPF", obligation_type=EntityType.EPF, amount_minor_units=to_minor_units(40000), start_date=as_of),
        RecurringObligation(org_id=org_id, name="EMI", obligation_type=EntityType.EMI, amount_minor_units=to_minor_units(110000), start_date=as_of),
        RecurringObligation(org_id=org_id, name="Rent", obligation_type=EntityType.RENT, amount_minor_units=to_minor_units(140000), start_date=as_of),
    ]
    scenario = ForecastScenario(
        name="Base Case",
        kind=ScenarioKind.BASE,
        description="Demo base assumptions",
        minimum_cash_buffer_minor_units=to_minor_units(600000),
    )
    return ForecastInput(
        profile=profile,
        as_of_date=as_of,
        opening_balance=BankBalanceSnapshot(org_id=org_id, as_of_date=as_of, balance_minor_units=to_minor_units(1800000)),
        inventory_snapshot=InventorySnapshot(org_id=org_id, as_of_date=as_of, inventory_minor_units=to_minor_units(1600000), raw_material_cover_days=23),
        counterparties=counterparties,
        events=events,
        obligations=obligations,
        scenario=scenario,
    )
