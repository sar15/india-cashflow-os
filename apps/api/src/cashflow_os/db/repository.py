"""
PostgreSQL-backed repository for Cashflow OS.

Implements the same interface as InMemoryStore but persists all data
to the Supabase PostgreSQL database via SQLAlchemy.  The repository
uses the 'cashflow' schema so it does not conflict with other apps
sharing the same Supabase project.

Heavy objects like ForecastRun and ReportPack are stored as JSONB
columns to avoid a complex relational mapping for deeply nested
Pydantic models while still gaining PostgreSQL durability and
query capability.
"""

import json
from datetime import date
from typing import Dict, List, Optional, Type, TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

from cashflow_os.db.engine import get_db_session
from cashflow_os.domain.models import (
    BankBalanceSnapshot,
    CanonicalCashEvent,
    Counterparty,
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
)
from cashflow_os.forecast.engine import build_forecast_run
from cashflow_os.reports.builder import build_report_pack
from cashflow_os.utils.money import to_minor_units


ModelT = TypeVar("ModelT")


class PostgresRepository:
    """PostgreSQL-backed store using the cashflow schema."""

    def __init__(self) -> None:
        self.report_file_cache: Dict[str, Dict[str, bytes]] = {}

    # ------------------------------------------------------------------
    # Organization
    # ------------------------------------------------------------------

    def ensure_org(self, org_id: str, company_name: str = "Unknown", industry: str = "Manufacturing") -> None:
        with get_db_session() as session:
            session.execute(
                text("""
                    INSERT INTO cashflow.organizations (org_id, company_name, industry)
                    VALUES (:org_id, :company_name, :industry)
                    ON CONFLICT (org_id) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        industry = EXCLUDED.industry,
                        updated_at = now()
                """),
                {"org_id": org_id, "company_name": company_name, "industry": industry},
            )

    # ------------------------------------------------------------------
    # Imports
    # ------------------------------------------------------------------

    def upsert_import(self, bundle: ParsedImportBundle) -> None:
        batch = bundle.import_batch
        bundle_json = bundle.model_dump(mode="json")

        with get_db_session() as session:
            self.ensure_org(batch.org_id)
            session.execute(
                text("""
                    INSERT INTO cashflow.import_batches
                        (import_batch_id, org_id, source_type, filename, checksum,
                         event_count, counterparty_count, obligation_count, unresolved_issues)
                    VALUES (:id, :org_id, :source_type, :filename, :checksum,
                            :event_count, :counterparty_count, :obligation_count, :issues::jsonb)
                    ON CONFLICT (import_batch_id) DO UPDATE SET
                        event_count = EXCLUDED.event_count,
                        counterparty_count = EXCLUDED.counterparty_count,
                        obligation_count = EXCLUDED.obligation_count,
                        unresolved_issues = EXCLUDED.unresolved_issues
                """),
                {
                    "id": batch.import_batch_id,
                    "org_id": batch.org_id,
                    "source_type": batch.source_type.value if hasattr(batch.source_type, "value") else str(batch.source_type),
                    "filename": batch.filename,
                    "checksum": batch.checksum,
                    "event_count": batch.event_count,
                    "counterparty_count": batch.counterparty_count,
                    "obligation_count": batch.obligation_count,
                    "issues": json.dumps([issue.model_dump(mode="json") for issue in batch.unresolved_issues]),
                },
            )

            for counterparty in bundle.counterparties:
                self._upsert_counterparty(session, counterparty, batch.org_id)

            for event in bundle.events:
                self._upsert_cash_event(session, event)

            for obligation in bundle.obligations:
                self._upsert_obligation(session, obligation)

            if bundle.bank_balance is not None:
                self._upsert_bank_snapshot(session, bundle.bank_balance)

            if bundle.inventory_snapshot is not None:
                self._upsert_inventory_snapshot(session, bundle.inventory_snapshot)

    def get_import(self, import_batch_id: str, *, org_id: Optional[str] = None) -> Optional[ParsedImportBundle]:
        with get_db_session() as session:
            if org_id:
                row = session.execute(
                    text("SELECT * FROM cashflow.import_batches WHERE import_batch_id = :id AND org_id = :org_id"),
                    {"id": import_batch_id, "org_id": org_id},
                ).mappings().first()
            else:
                row = session.execute(
                    text("SELECT * FROM cashflow.import_batches WHERE import_batch_id = :id"),
                    {"id": import_batch_id},
                ).mappings().first()
            if row is None:
                return None

            events = [
                CanonicalCashEvent.model_validate(dict(r))
                for r in session.execute(
                    text("SELECT * FROM cashflow.cash_events WHERE import_batch_id = :id"),
                    {"id": import_batch_id},
                ).mappings().all()
            ] if True else []

            counterparties_rows = session.execute(
                text("SELECT * FROM cashflow.counterparties WHERE org_id = :org_id"),
                {"org_id": row["org_id"]},
            ).mappings().all()
            counterparties = [Counterparty.model_validate(dict(r)) for r in counterparties_rows]

            obligations_rows = session.execute(
                text("SELECT * FROM cashflow.recurring_obligations WHERE org_id = :org_id"),
                {"org_id": row["org_id"]},
            ).mappings().all()
            obligations = [RecurringObligation.model_validate(dict(r)) for r in obligations_rows]

            bank_row = session.execute(
                text("SELECT * FROM cashflow.bank_balance_snapshots WHERE org_id = :org_id ORDER BY as_of_date DESC LIMIT 1"),
                {"org_id": row["org_id"]},
            ).mappings().first()
            bank_balance = BankBalanceSnapshot.model_validate(dict(bank_row)) if bank_row else None

            inv_row = session.execute(
                text("SELECT * FROM cashflow.inventory_snapshots WHERE org_id = :org_id ORDER BY as_of_date DESC LIMIT 1"),
                {"org_id": row["org_id"]},
            ).mappings().first()
            inventory = InventorySnapshot.model_validate(dict(inv_row)) if inv_row else None

            unresolved_issues = row["unresolved_issues"] if isinstance(row["unresolved_issues"], list) else json.loads(row["unresolved_issues"] or "[]")

            return ParsedImportBundle(
                import_batch=ImportBatch(
                    import_batch_id=row["import_batch_id"],
                    org_id=row["org_id"],
                    source_type=SourceType(row["source_type"]),
                    filename=row["filename"],
                    checksum=row["checksum"],
                    event_count=row["event_count"],
                    counterparty_count=row["counterparty_count"],
                    obligation_count=row["obligation_count"],
                    unresolved_issues=unresolved_issues,
                ),
                counterparties=counterparties,
                events=events,
                obligations=obligations,
                bank_balance=bank_balance,
                inventory_snapshot=inventory,
            )

    def find_import_by_checksum(self, org_id: str, source_type: SourceType, checksum: Optional[str]) -> Optional[ParsedImportBundle]:
        if not checksum:
            return None
        with get_db_session() as session:
            row = session.execute(
                text("""
                    SELECT import_batch_id FROM cashflow.import_batches
                    WHERE org_id = :org_id AND source_type = :source_type AND checksum = :checksum
                    LIMIT 1
                """),
                {"org_id": org_id, "source_type": source_type.value, "checksum": checksum},
            ).mappings().first()
            if row is None:
                return None
            return self.get_import(row["import_batch_id"])

    # ------------------------------------------------------------------
    # Cash Events
    # ------------------------------------------------------------------

    def _upsert_cash_event(self, session: Session, event: CanonicalCashEvent) -> None:
        session.execute(
            text("""
                INSERT INTO cashflow.cash_events
                    (event_id, org_id, source_id, import_batch_id, event_type, entity_type,
                     counterparty_id, counterparty_name, document_number, document_date,
                     due_date, expected_cash_date, gross_minor_units, tax_minor_units,
                     tds_minor_units, net_minor_units, currency, status,
                     source_confidence, mapping_confidence, rule_version, forecast_inclusion_status)
                VALUES (:event_id, :org_id, :source_id, :import_batch_id, :event_type, :entity_type,
                        :counterparty_id, :counterparty_name, :document_number, :document_date,
                        :due_date, :expected_cash_date, :gross, :tax, :tds, :net,
                        :currency, :status, :source_conf, :mapping_conf, :rule_ver, :inclusion)
                ON CONFLICT (event_id) DO UPDATE SET
                    net_minor_units = EXCLUDED.net_minor_units,
                    status = EXCLUDED.status,
                    expected_cash_date = EXCLUDED.expected_cash_date,
                    updated_at = now()
            """),
            {
                "event_id": event.event_id,
                "org_id": event.org_id,
                "source_id": event.source_id,
                "import_batch_id": event.import_batch_id,
                "event_type": event.event_type.value,
                "entity_type": event.entity_type.value,
                "counterparty_id": event.counterparty_id,
                "counterparty_name": event.counterparty_name,
                "document_number": event.document_number,
                "document_date": event.document_date,
                "due_date": event.due_date,
                "expected_cash_date": event.expected_cash_date,
                "gross": event.gross_minor_units,
                "tax": event.tax_minor_units,
                "tds": event.tds_minor_units,
                "net": event.net_minor_units,
                "currency": event.currency,
                "status": event.status.value,
                "source_conf": float(event.source_confidence),
                "mapping_conf": float(event.mapping_confidence),
                "rule_ver": event.rule_version,
                "inclusion": event.forecast_inclusion_status,
            },
        )

    # ------------------------------------------------------------------
    # Counterparties
    # ------------------------------------------------------------------

    def _upsert_counterparty(self, session: Session, counterparty: Counterparty, org_id: str) -> None:
        session.execute(
            text("""
                INSERT INTO cashflow.counterparties
                    (counterparty_id, org_id, entity_name, relationship_type,
                     is_msme_registered, behavioral_delay_days, collection_confidence)
                VALUES (:id, :org_id, :name, :rel, :msme, :delay, :conf)
                ON CONFLICT (counterparty_id) DO UPDATE SET
                    entity_name = EXCLUDED.entity_name,
                    is_msme_registered = EXCLUDED.is_msme_registered,
                    behavioral_delay_days = EXCLUDED.behavioral_delay_days,
                    collection_confidence = EXCLUDED.collection_confidence,
                    updated_at = now()
            """),
            {
                "id": counterparty.counterparty_id,
                "org_id": org_id,
                "name": counterparty.entity_name,
                "rel": counterparty.relationship_type.value,
                "msme": counterparty.is_msme_registered,
                "delay": counterparty.behavioral_delay_days,
                "conf": float(counterparty.collection_confidence),
            },
        )

    # ------------------------------------------------------------------
    # Obligations
    # ------------------------------------------------------------------

    def _upsert_obligation(self, session: Session, obligation: RecurringObligation) -> None:
        session.execute(
            text("""
                INSERT INTO cashflow.recurring_obligations
                    (obligation_id, org_id, name, obligation_type, frequency,
                     amount_minor_units, due_day, start_date, end_date, notes)
                VALUES (:id, :org_id, :name, :type, :freq, :amount, :day, :start, :end, :notes)
                ON CONFLICT (obligation_id) DO UPDATE SET
                    amount_minor_units = EXCLUDED.amount_minor_units,
                    name = EXCLUDED.name
            """),
            {
                "id": obligation.obligation_id,
                "org_id": obligation.org_id,
                "name": obligation.name,
                "type": obligation.obligation_type.value,
                "freq": obligation.frequency,
                "amount": obligation.amount_minor_units,
                "day": obligation.due_day,
                "start": obligation.start_date,
                "end": obligation.end_date,
                "notes": obligation.notes,
            },
        )

    def add_obligation(self, obligation: RecurringObligation) -> None:
        with get_db_session() as session:
            self._upsert_obligation(session, obligation)

    def get_obligations(self, org_id: str) -> List[RecurringObligation]:
        with get_db_session() as session:
            rows = session.execute(
                text("SELECT * FROM cashflow.recurring_obligations WHERE org_id = :org_id"),
                {"org_id": org_id},
            ).mappings().all()
            return [RecurringObligation.model_validate(dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Bank / Inventory Snapshots
    # ------------------------------------------------------------------

    def _upsert_bank_snapshot(self, session: Session, snapshot: BankBalanceSnapshot) -> None:
        session.execute(
            text("""
                INSERT INTO cashflow.bank_balance_snapshots
                    (snapshot_id, org_id, account_name, as_of_date, balance_minor_units)
                VALUES (gen_random_uuid()::text, :org_id, :account, :date, :balance)
            """),
            {
                "org_id": snapshot.org_id,
                "account": getattr(snapshot, "account_name", "Primary"),
                "date": snapshot.as_of_date,
                "balance": snapshot.balance_minor_units,
            },
        )

    def _upsert_inventory_snapshot(self, session: Session, snapshot: InventorySnapshot) -> None:
        session.execute(
            text("""
                INSERT INTO cashflow.inventory_snapshots
                    (snapshot_id, org_id, as_of_date, inventory_minor_units, raw_material_cover_days)
                VALUES (gen_random_uuid()::text, :org_id, :date, :inventory, :cover)
            """),
            {
                "org_id": snapshot.org_id,
                "date": snapshot.as_of_date,
                "inventory": snapshot.inventory_minor_units,
                "cover": snapshot.raw_material_cover_days,
            },
        )

    # ------------------------------------------------------------------
    # Forecast Inputs / Runs / Scenarios
    # ------------------------------------------------------------------

    def upsert_scenario(self, scenario: ForecastScenario) -> None:
        with get_db_session() as session:
            session.execute(
                text("""
                    INSERT INTO cashflow.forecast_scenarios
                        (scenario_id, org_id, name, kind, description,
                         inflow_delay_days, outflow_delay_days,
                         inflow_scalar_bps, outflow_scalar_bps,
                         opening_cash_adjustment_minor_units, minimum_cash_buffer_minor_units)
                    VALUES (:id, :org_id, :name, :kind, :desc,
                            :inflow_delay, :outflow_delay,
                            :inflow_bps, :outflow_bps,
                            :cash_adj, :min_buffer)
                    ON CONFLICT (scenario_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description
                """),
                {
                    "id": scenario.scenario_id,
                    "org_id": getattr(scenario, "org_id", "demo-org"),
                    "name": scenario.name,
                    "kind": scenario.kind.value,
                    "desc": scenario.description,
                    "inflow_delay": scenario.inflow_delay_days,
                    "outflow_delay": scenario.outflow_delay_days,
                    "inflow_bps": scenario.inflow_scalar_bps,
                    "outflow_bps": scenario.outflow_scalar_bps,
                    "cash_adj": scenario.opening_cash_adjustment_minor_units,
                    "min_buffer": scenario.minimum_cash_buffer_minor_units,
                },
            )

    def upsert_forecast_input(self, key: str, forecast_input: ForecastInput) -> None:
        pass

    def upsert_forecast_run(self, run: ForecastRun, forecast_input: Optional[ForecastInput] = None) -> None:
        run_json = run.model_dump(mode="json")
        input_json = forecast_input.model_dump(mode="json") if forecast_input else {}

        with get_db_session() as session:
            self.ensure_org(run.profile.org_id, run.profile.company_name, run.profile.industry)
            session.execute(
                text("""
                    INSERT INTO cashflow.forecast_runs
                        (forecast_run_id, org_id, as_of_date, opening_balance_minor_units,
                         horizon_days, calendar_version, rule_version,
                         scenario_snapshot, profile_snapshot,
                         weekly_buckets, resolved_events, kpis, alerts, audit_trace,
                         input_snapshot)
                    VALUES (:id, :org_id, :as_of, :opening, :horizon,
                            :cal_ver, :rule_ver,
                            :scenario::jsonb, :profile::jsonb,
                            :weekly::jsonb, :events::jsonb, :kpis::jsonb,
                            :alerts::jsonb, :trace::jsonb, :input::jsonb)
                    ON CONFLICT (forecast_run_id) DO UPDATE SET
                        weekly_buckets = EXCLUDED.weekly_buckets,
                        resolved_events = EXCLUDED.resolved_events,
                        kpis = EXCLUDED.kpis,
                        alerts = EXCLUDED.alerts,
                        audit_trace = EXCLUDED.audit_trace
                """),
                {
                    "id": run.forecast_run_id,
                    "org_id": run.profile.org_id,
                    "as_of": run.as_of_date.isoformat(),
                    "opening": run.opening_balance_minor_units,
                    "horizon": run.horizon_days,
                    "cal_ver": run.calendar_version,
                    "rule_ver": run.rule_version,
                    "scenario": json.dumps(run_json.get("scenario", {})),
                    "profile": json.dumps(run_json.get("profile", {})),
                    "weekly": json.dumps(run_json.get("weekly_buckets", [])),
                    "events": json.dumps(run_json.get("resolved_events", [])),
                    "kpis": json.dumps(run_json.get("kpis", {})),
                    "alerts": json.dumps(run_json.get("alerts", [])),
                    "trace": json.dumps(run_json.get("audit_trace", [])),
                    "input": json.dumps(input_json),
                },
            )

    def get_forecast_run(self, forecast_run_id: str, *, org_id: Optional[str] = None) -> Optional[ForecastRun]:
        with get_db_session() as session:
            if org_id:
                row = session.execute(
                    text("SELECT * FROM cashflow.forecast_runs WHERE forecast_run_id = :id AND org_id = :org_id"),
                    {"id": forecast_run_id, "org_id": org_id},
                ).mappings().first()
            else:
                row = session.execute(
                    text("SELECT * FROM cashflow.forecast_runs WHERE forecast_run_id = :id"),
                    {"id": forecast_run_id},
                ).mappings().first()
            if row is None:
                return None
            return self._row_to_forecast_run(dict(row))

    def get_latest_forecast_run(self, org_id: str) -> Optional[ForecastRun]:
        with get_db_session() as session:
            row = session.execute(
                text("SELECT * FROM cashflow.forecast_runs WHERE org_id = :org_id ORDER BY created_at DESC LIMIT 1"),
                {"org_id": org_id},
            ).mappings().first()
            if row is None:
                return None
            return self._row_to_forecast_run(dict(row))

    def get_forecast_input(self, key: str, *, org_id: Optional[str] = None) -> Optional[ForecastInput]:
        with get_db_session() as session:
            if org_id:
                row = session.execute(
                    text("SELECT input_snapshot FROM cashflow.forecast_runs WHERE forecast_run_id = :id AND org_id = :org_id"),
                    {"id": key, "org_id": org_id},
                ).mappings().first()
            else:
                row = session.execute(
                    text("SELECT input_snapshot FROM cashflow.forecast_runs WHERE forecast_run_id = :id"),
                    {"id": key},
                ).mappings().first()
            if row is None:
                return None
            snapshot = row["input_snapshot"]
            if isinstance(snapshot, str):
                snapshot = json.loads(snapshot)
            if not snapshot:
                return None
            return ForecastInput.model_validate(snapshot)

    def _row_to_forecast_run(self, row: dict) -> ForecastRun:
        def _parse_jsonb(value):
            if isinstance(value, str):
                return json.loads(value)
            return value

        return ForecastRun.model_validate({
            "forecast_run_id": row["forecast_run_id"],
            "as_of_date": row["as_of_date"],
            "opening_balance_minor_units": row["opening_balance_minor_units"],
            "horizon_days": row["horizon_days"],
            "calendar_version": row.get("calendar_version"),
            "rule_version": row.get("rule_version"),
            "scenario": _parse_jsonb(row.get("scenario_snapshot", {})),
            "profile": _parse_jsonb(row.get("profile_snapshot", {})),
            "weekly_buckets": _parse_jsonb(row.get("weekly_buckets", [])),
            "resolved_events": _parse_jsonb(row.get("resolved_events", [])),
            "kpis": _parse_jsonb(row.get("kpis", {})),
            "alerts": _parse_jsonb(row.get("alerts", [])),
            "audit_trace": _parse_jsonb(row.get("audit_trace", [])),
        })

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def upsert_report(self, report: ReportPack) -> None:
        report_json = report.model_dump(mode="json")
        with get_db_session() as session:
            run_row = session.execute(
                text("SELECT org_id FROM cashflow.forecast_runs WHERE forecast_run_id = :id"),
                {"id": report.forecast_run_id},
            ).mappings().first()
            org_id = run_row["org_id"] if run_row else "demo-org"

            session.execute(
                text("""
                    INSERT INTO cashflow.report_packs
                        (report_id, forecast_run_id, org_id, title, charts, sections, methodology_notes)
                    VALUES (:id, :run_id, :org_id, :title, :charts::jsonb, :sections::jsonb, :notes::jsonb)
                    ON CONFLICT (report_id) DO UPDATE SET
                        charts = EXCLUDED.charts,
                        sections = EXCLUDED.sections
                """),
                {
                    "id": report.report_id,
                    "run_id": report.forecast_run_id,
                    "org_id": org_id,
                    "title": report.title,
                    "charts": json.dumps(report_json.get("charts", [])),
                    "sections": json.dumps(report_json.get("sections", [])),
                    "notes": json.dumps(report_json.get("methodology_notes", [])),
                },
            )

    def get_report(self, report_id: str, *, org_id: Optional[str] = None) -> Optional[ReportPack]:
        with get_db_session() as session:
            if org_id:
                row = session.execute(
                    text("SELECT * FROM cashflow.report_packs WHERE report_id = :id AND org_id = :org_id"),
                    {"id": report_id, "org_id": org_id},
                ).mappings().first()
            else:
                row = session.execute(
                    text("SELECT * FROM cashflow.report_packs WHERE report_id = :id"),
                    {"id": report_id},
                ).mappings().first()
            if row is None:
                return None
            return self._row_to_report_pack(dict(row))

    def get_report_by_run(self, forecast_run_id: str, *, org_id: Optional[str] = None) -> Optional[ReportPack]:
        with get_db_session() as session:
            if org_id:
                row = session.execute(
                    text("SELECT * FROM cashflow.report_packs WHERE forecast_run_id = :id AND org_id = :org_id ORDER BY created_at DESC LIMIT 1"),
                    {"id": forecast_run_id, "org_id": org_id},
                ).mappings().first()
            else:
                row = session.execute(
                    text("SELECT * FROM cashflow.report_packs WHERE forecast_run_id = :id ORDER BY created_at DESC LIMIT 1"),
                    {"id": forecast_run_id},
                ).mappings().first()
            if row is None:
                return None
            return self._row_to_report_pack(dict(row))

    def _row_to_report_pack(self, row: dict) -> ReportPack:
        def _parse_jsonb(value):
            if isinstance(value, str):
                return json.loads(value)
            return value

        return ReportPack.model_validate({
            "report_id": row["report_id"],
            "forecast_run_id": row["forecast_run_id"],
            "title": row["title"],
            "charts": _parse_jsonb(row.get("charts", [])),
            "sections": _parse_jsonb(row.get("sections", [])),
            "methodology_notes": _parse_jsonb(row.get("methodology_notes", [])),
        })

    def cache_report_file(self, report_id: str, file_format: str, content: bytes) -> None:
        self.report_file_cache.setdefault(report_id, {})[file_format] = content
        with get_db_session() as session:
            path = "cashflow-reports/{report_id}.{fmt}".format(report_id=report_id, fmt=file_format)
            if file_format == "pdf":
                session.execute(
                    text("UPDATE cashflow.report_packs SET pdf_storage_path = :path WHERE report_id = :id"),
                    {"path": path, "id": report_id},
                )
            else:
                session.execute(
                    text("UPDATE cashflow.report_packs SET xlsx_storage_path = :path WHERE report_id = :id"),
                    {"path": path, "id": report_id},
                )

    def read_report_file(self, report_id: str, file_format: str) -> Optional[bytes]:
        return self.report_file_cache.get(report_id, {}).get(file_format)


    # ------------------------------------------------------------------
    # Listing helpers for API
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Seed demo data
    # ------------------------------------------------------------------

    def seed_demo(self) -> None:
        try:
            with get_db_session() as session:
                row = session.execute(
                    text("SELECT COUNT(*) as cnt FROM cashflow.forecast_runs"),
                ).mappings().first()
                if row and row["cnt"] > 0:
                    return

            from cashflow_os.api.store import build_demo_forecast_input
            demo_input = build_demo_forecast_input()
            from cashflow_os.forecast.engine import build_forecast_run
            from cashflow_os.reports.builder import build_report_pack
            demo_run = build_forecast_run(demo_input)
            demo_report = build_report_pack(demo_run)
            self.upsert_forecast_run(demo_run, demo_input)
            self.upsert_report(demo_report)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Listing helpers for API
    # ------------------------------------------------------------------

    @property
    def forecast_runs(self) -> Dict[str, ForecastRun]:
        with get_db_session() as session:
            rows = session.execute(
                text("SELECT * FROM cashflow.forecast_runs ORDER BY created_at DESC LIMIT 50"),
            ).mappings().all()
            return {row["forecast_run_id"]: self._row_to_forecast_run(dict(row)) for row in rows}

    @property
    def reports(self) -> Dict[str, ReportPack]:
        with get_db_session() as session:
            rows = session.execute(
                text("SELECT * FROM cashflow.report_packs ORDER BY created_at DESC LIMIT 50"),
            ).mappings().all()
            return {row["report_id"]: self._row_to_report_pack(dict(row)) for row in rows}

    @property
    def imports(self) -> Dict[str, ParsedImportBundle]:
        result = {}
        with get_db_session() as session:
            rows = session.execute(
                text("SELECT import_batch_id FROM cashflow.import_batches ORDER BY created_at DESC LIMIT 50"),
            ).mappings().all()
        for row in rows:
            bundle = self.get_import(row["import_batch_id"])
            if bundle:
                result[row["import_batch_id"]] = bundle
        return result

    @property
    def scenarios(self) -> Dict[str, ForecastScenario]:
        with get_db_session() as session:
            rows = session.execute(
                text("SELECT * FROM cashflow.forecast_scenarios ORDER BY created_at DESC LIMIT 50"),
            ).mappings().all()
            return {row["scenario_id"]: ForecastScenario.model_validate(dict(row)) for row in rows}



    @property
    def forecast_inputs(self) -> Dict[str, ForecastInput]:
        with get_db_session() as session:
            rows = session.execute(
                text("SELECT forecast_run_id, input_snapshot FROM cashflow.forecast_runs WHERE input_snapshot != '{}'::jsonb ORDER BY created_at DESC LIMIT 50"),
            ).mappings().all()
            result = {}
            for row in rows:
                snapshot = row["input_snapshot"]
                if isinstance(snapshot, str):
                    snapshot = json.loads(snapshot)
                if snapshot:
                    try:
                        result[row["forecast_run_id"]] = ForecastInput.model_validate(snapshot)
                    except Exception:
                        pass
            return result

    @property
    def obligations(self) -> Dict[str, List[RecurringObligation]]:
        with get_db_session() as session:
            rows = session.execute(
                text("SELECT * FROM cashflow.recurring_obligations ORDER BY created_at DESC"),
            ).mappings().all()
            result: Dict[str, List[RecurringObligation]] = {}
            for row in rows:
                ob = RecurringObligation.model_validate(dict(row))
                result.setdefault(ob.org_id, []).append(ob)
            return result
