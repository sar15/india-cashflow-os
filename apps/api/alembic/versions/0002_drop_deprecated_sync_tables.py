"""drop deprecated sync tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-01

Removes the source_connections, oauth_states, and desktop_agents tables
that were part of the Zoho OAuth and Desktop Sync Agent features.
These features have been removed as part of the manual-upload-only pivot.

NOTE: This migration is safe to run at any time. The application no longer
references these tables. They may still contain historical data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cashflow.desktop_agents CASCADE")
    op.execute("DROP TABLE IF EXISTS cashflow.oauth_states CASCADE")
    op.execute("DROP TABLE IF EXISTS cashflow.source_connections CASCADE")


def downgrade() -> None:
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

    op.execute("""
        CREATE TABLE IF NOT EXISTS cashflow.oauth_states (
            state           TEXT PRIMARY KEY,
            connection_id   TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

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

    for table in ["source_connections", "desktop_agents"]:
        op.execute("ALTER TABLE cashflow.{table} ENABLE ROW LEVEL SECURITY".format(table=table))
