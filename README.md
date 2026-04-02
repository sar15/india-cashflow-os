# India Cashflow OS

India-first cash forecasting platform for SMEs, CAs, and operating finance teams.

- `apps/api`: FastAPI backend with a deterministic cash forecast engine, strict IST timezone consistency, India compliance rules, SQLAlchemy/SQLite persistence, authenticated HTTP API, KPI builders, and robust test suite.
- `apps/web`: Next.js App Router frontend featuring a brutally simple MVP flow: Upload -> Review Exceptions -> Dashboard.
- `templates`: Import templates for manual onboarding.
- `docs`: Implementation notes and local setup references.

## What is implemented

- Deterministic 13-week direct cash forecast engine.
- India rules for GST, TDS, EPF, payroll, EMI, and MSME 45-day payable risk (Section 43B(h)).
- Canonical cash-event model with audit trace support.
- KPI layer and chart/report specification generation.
- Persistent FastAPI using SQLAlchemy and SQLite for durability across restarts.
- Role-based API authentication with owner, finance manager, accountant, and viewer roles.
- **MVP Ingestion Flow** — Tally exports (CSV/XML/XLSX) and a standard Cashflow OS template (XLSX/CSV) via drag-and-drop.
- 50 MB upload limit with extension-based file validation.
- Row-level parsing error feedback and exception review UI.
- Downloadable `.xlsx` template with sample data at `GET /v1/templates/cashflow-os-template.xlsx`.
- Clean Next.js onboarding journey for import, exception patching, forecast creation, dashboard viewing, and report export.
- Signed web sessions with deploy-safe user configuration.
- Checksum-based import deduplication.

## Quick start

### API

```bash
cd apps/api
cp .env.example .env
python3 -m uvicorn --app-dir src cashflow_os.api.main:app --reload
```
Data persists automatically to a local SQLite database file `data/cashflow-os.db`.

### Tests

```bash
cd apps/api
PYTHONPATH=src python3 -m pytest tests/ -v
```

### Web

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

### Local-first infra

```bash
docker compose -f compose.local.yml up -d
```
This brings up free local `Postgres` and `Redis` if you'd like to prepare for scale.

## Free deployment

Generate deploy-safe session and API token configuration:

```bash
node scripts/generate_auth_bundle.mjs --email owner@company.com --name "Owner" --password "choose-a-strong-password"
```

Deployment notes live in `docs/FREE_DEPLOYMENT.md`.

## Notes

- Money is stored and computed strictly as integer paise, not floats.
- Forecast arithmetic is deterministic and traceable.
- All time-sensitive calculations strictly enforce the Asia/Kolkata (IST) timezone to avoid mid-night boundary shifts.
- API state persists to `data/cashflow-os.db` via SQLAlchemy.
- Generated PDF/XLSX exports persist to the local filesystem under `data/report-files`.
- Duplicate imports are deduplicated by checksum per org and source type to prevent ledger drift.
- Default local API tokens are:
  - `demo-owner-token`
  - `demo-finance-token`
  - `demo-accountant-token`
  - `demo-viewer-token`
- Allowed web origins default to `http://localhost:3000` and `http://127.0.0.1:3000`.
- Real-world forecast accuracy still depends on input quality and assumptions.
