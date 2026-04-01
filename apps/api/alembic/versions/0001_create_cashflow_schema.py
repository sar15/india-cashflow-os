"""create cashflow schema and all tables

Revision ID: 0001
Revises: None
Create Date: 2026-04-01

Defines every table in the cashflow schema as used by
PostgresRepository.  All money columns are BIGINT (paise).
Complex nested models use JSONB for flexibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS cashflow")

    # ── organizations ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.organizations (
            org_id          TEXT PRIMARY KEY,
            company_name    TEXT NOT NULL DEFAULT 'Unknown',
            industry        TEXT NOT NULL DEFAULT 'Manufacturing',
            reporting_tz    TEXT NOT NULL DEFAULT 'Asia/Kolkata',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ── import_batches ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.import_batches (
            import_batch_id     TEXT PRIMARY KEY,
            org_id              TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            source_type         TEXT NOT NULL DEFAULT 'manual',
            filename            TEXT,
            checksum            TEXT,
            event_count         INTEGER NOT NULL DEFAULT 0,
            counterparty_count  INTEGER NOT NULL DEFAULT 0,
            obligation_count    INTEGER NOT NULL DEFAULT 0,
            unresolved_issues   JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_import_batches_org ON cashflow.import_batches(org_id)")

    # ── counterparties ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.counterparties (
            counterparty_id         TEXT PRIMARY KEY,
            org_id                  TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            entity_name             TEXT NOT NULL,
            relationship_type       TEXT NOT NULL DEFAULT 'customer',
            is_msme_registered      BOOLEAN NOT NULL DEFAULT FALSE,
            collection_confidence   DOUBLE PRECISION NOT NULL DEFAULT 0.85,
            payment_terms_days      INTEGER,
            notes                   TEXT,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_counterparties_org ON cashflow.counterparties(org_id)")

    # ── cash_events ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.cash_events (
            event_id            TEXT PRIMARY KEY,
            org_id              TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            source_id           TEXT NOT NULL,
            import_batch_id     TEXT REFERENCES cashflow.import_batches(import_batch_id),
            event_type          TEXT NOT NULL,
            entity_type         TEXT NOT NULL DEFAULT 'invoice',
            counterparty_id     TEXT,
            counterparty_name   TEXT,
            document_number     TEXT,
            document_date       DATE,
            due_date            DATE,
            gross_minor_units   BIGINT NOT NULL DEFAULT 0,
            tax_minor_units     BIGINT NOT NULL DEFAULT 0,
            tds_minor_units     BIGINT NOT NULL DEFAULT 0,
            net_minor_units     BIGINT NOT NULL DEFAULT 0,
            status              TEXT NOT NULL DEFAULT 'open',
            source_confidence   DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            mapping_confidence  DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            notes               TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cash_events_org ON cashflow.cash_events(org_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cash_events_batch ON cashflow.cash_events(import_batch_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cash_events_due ON cashflow.cash_events(due_date)")

    # ── recurring_obligations ────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.recurring_obligations (
            obligation_id           TEXT PRIMARY KEY,
            org_id                  TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            name                    TEXT NOT NULL,
            obligation_type         TEXT NOT NULL,
            frequency               TEXT NOT NULL DEFAULT 'monthly',
            amount_minor_units      BIGINT NOT NULL DEFAULT 0,
            due_day                 INTEGER,
            start_date              DATE NOT NULL,
            end_date                DATE,
            notes                   TEXT,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_obligations_org ON cashflow.recurring_obligations(org_id)")

    # ── bank_balance_snapshots ───────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.bank_balance_snapshots (
            snapshot_id         TEXT PRIMARY KEY,
            org_id              TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            account_name        TEXT NOT NULL DEFAULT 'Primary',
            as_of_date          DATE NOT NULL,
            balance_minor_units BIGINT NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_snapshots_org ON cashflow.bank_balance_snapshots(org_id)")

    # ── inventory_snapshots ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.inventory_snapshots (
            snapshot_id             TEXT PRIMARY KEY,
            org_id                  TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            as_of_date              DATE NOT NULL,
            inventory_minor_units   BIGINT NOT NULL DEFAULT 0,
            raw_material_cover_days INTEGER NOT NULL DEFAULT 0,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_org ON cashflow.inventory_snapshots(org_id)")

    # ── forecast_scenarios ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.forecast_scenarios (
            scenario_id                         TEXT PRIMARY KEY,
            org_id                              TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            name                                TEXT NOT NULL,
            kind                                TEXT NOT NULL DEFAULT 'base',
            description                         TEXT,
            inflow_delay_days                   INTEGER NOT NULL DEFAULT 0,
            outflow_delay_days                  INTEGER NOT NULL DEFAULT 0,
            inflow_scalar_bps                   INTEGER NOT NULL DEFAULT 10000,
            outflow_scalar_bps                  INTEGER NOT NULL DEFAULT 10000,
            opening_cash_adjustment_minor_units BIGINT NOT NULL DEFAULT 0,
            minimum_cash_buffer_minor_units     BIGINT NOT NULL DEFAULT 0,
            created_at                          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_org ON cashflow.forecast_scenarios(org_id)")

    # ── forecast_runs (JSONB-heavy) ──────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.forecast_runs (
            forecast_run_id             TEXT PRIMARY KEY,
            org_id                      TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            as_of_date                  DATE NOT NULL,
            opening_balance_minor_units BIGINT NOT NULL DEFAULT 0,
            horizon_days                INTEGER NOT NULL DEFAULT 91,
            calendar_version            TEXT,
            rule_version                TEXT,
            scenario_snapshot           JSONB NOT NULL DEFAULT '{}'::jsonb,
            profile_snapshot            JSONB NOT NULL DEFAULT '{}'::jsonb,
            weekly_buckets              JSONB NOT NULL DEFAULT '[]'::jsonb,
            resolved_events             JSONB NOT NULL DEFAULT '[]'::jsonb,
            kpis                        JSONB NOT NULL DEFAULT '{}'::jsonb,
            alerts                      JSONB NOT NULL DEFAULT '[]'::jsonb,
            audit_trace                 JSONB NOT NULL DEFAULT '[]'::jsonb,
            input_snapshot              JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_forecast_runs_org ON cashflow.forecast_runs(org_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_forecast_runs_date ON cashflow.forecast_runs(as_of_date)")

    # ── report_packs (JSONB-heavy) ───────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.report_packs (
            report_id           TEXT PRIMARY KEY,
            forecast_run_id     TEXT NOT NULL REFERENCES cashflow.forecast_runs(forecast_run_id),
            org_id              TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            title               TEXT NOT NULL,
            charts              JSONB NOT NULL DEFAULT '[]'::jsonb,
            sections            JSONB NOT NULL DEFAULT '[]'::jsonb,
            methodology_notes   JSONB NOT NULL DEFAULT '[]'::jsonb,
            pdf_storage_path    TEXT,
            xlsx_storage_path   TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_report_packs_org ON cashflow.report_packs(org_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_report_packs_run ON cashflow.report_packs(forecast_run_id)")

    # ── source_connections ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.source_connections (
            connection_id       TEXT PRIMARY KEY,
            org_id              TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            source_type         TEXT NOT NULL DEFAULT 'zoho',
            client_name         TEXT,
            status              TEXT NOT NULL DEFAULT 'pending',
            redirect_uri        TEXT,
            token_payload       JSONB,
            remote_org_id       TEXT,
            remote_org_name     TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_source_connections_org ON cashflow.source_connections(org_id)")

    # ── oauth_states (ephemeral, auto-consumed) ──────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.oauth_states (
            state           TEXT PRIMARY KEY,
            connection_id   TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ── desktop_agents ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.desktop_agents (
            agent_id            TEXT PRIMARY KEY,
            org_id              TEXT NOT NULL REFERENCES cashflow.organizations(org_id),
            machine_name        TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'offline',
            watched_path        TEXT,
            last_heartbeat_at   TIMESTAMPTZ,
            last_message        TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_desktop_agents_org ON cashflow.desktop_agents(org_id)")

    # ── Row Level Security ───────────────────────────────────────────
    # Enable RLS on all tenant-scoped tables (enforced at Supabase layer)
    _tenant_tables = [
        "organizations", "import_batches", "counterparties", "cash_events",
        "recurring_obligations", "bank_balance_snapshots", "inventory_snapshots",
        "forecast_scenarios", "forecast_runs", "report_packs",
        "source_connections", "desktop_agents",
    ]
    for table in _tenant_tables:
        op.execute("ALTER TABLE cashflow.{table} ENABLE ROW LEVEL SECURITY".format(table=table))


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS cashflow CASCADE")
