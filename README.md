# India Cashflow OS

India-first cash forecasting platform for SMEs, CAs, and operating finance teams.

This repository now contains a working MVP foundation:

- `apps/api`: FastAPI backend with deterministic cash forecast engine, India compliance rules, persistent local state, authenticated API access, KPI/report builders, Excel/PDF exports, and tests.
- `apps/web`: Next.js App Router frontend with live import/setup flows, dashboard reporting, and export proxy routes.
- `templates`: import templates for manual onboarding.
- `docs`: implementation notes and API/reporting references.

## What is implemented

- Deterministic 13-week direct cash forecast engine.
- India rules for GST, TDS, EPF, payroll, EMI, and MSME 45-day payable risk.
- Canonical cash-event model with audit trace support.
- KPI layer and chart/report specification generation.
- PDF and Excel report export foundation.
- Persistent FastAPI API surface aligned to the planned endpoints.
- Role-based API authentication with owner, finance manager, accountant, and viewer roles.
- Tally, Zoho, and manual-template ingestion foundations.
- Live Next.js onboarding flow for import, mapping confirmation, forecast creation, dashboard viewing, and report export.
- Signed web sessions with deploy-safe user configuration.
- Live Zoho OAuth callback + sync flow for invoices and bills when Zoho credentials are configured.
- Free-tier Vercel deployment path with Blob-backed persistence in `docs/FREE_DEPLOYMENT.md`.

## Quick start

### API

```bash
cd apps/api
cp .env.example .env
python3 -m uvicorn --app-dir src cashflow_os.api.main:app --reload
```

### Tests

```bash
cd apps/api
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
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

This brings up free local `Postgres`, `Redis`, and `MinIO`. The API can stay on lightweight file storage for the fastest start, or switch to local MinIO by setting `CASHFLOW_STORAGE_BACKEND=minio` in `apps/api/.env`.

### Desktop sync agent

```bash
cd apps/desktop_agent
cp .env.example .env
python3 main.py --once
```

The desktop agent registers the machine, heartbeats its watch folder, and uploads new files through the existing authenticated API.

## Free deployment

Generate deploy-safe session and API token configuration:

```bash
node scripts/generate_auth_bundle.mjs --email owner@company.com --name "Owner" --password "choose-a-strong-password"
```

Deployment notes live in `docs/FREE_DEPLOYMENT.md`.

## Notes

- Money is stored as integer paise, not floats.
- Forecast arithmetic is deterministic and traceable.
- API state persists to `data/cashflow-os-state.json` by default and can be overridden with `CASHFLOW_STATE_PATH`.
- Generated PDF/XLSX exports persist to `data/report-files` by default and can be overridden with `CASHFLOW_REPORT_STORAGE_PATH`.
- Duplicate imports are deduplicated by checksum per org and source type so repeated uploads return the same import batch instead of creating drift.
- Default local API tokens are:
  - `demo-owner-token`
  - `demo-finance-token`
  - `demo-accountant-token`
  - `demo-viewer-token`
- Allowed web origins default to `http://localhost:3000` and `http://127.0.0.1:3000`, configurable via `CASHFLOW_ALLOWED_ORIGINS`.
- Demo web users are meant for local development only and can be disabled with `CASHFLOW_DISABLE_DEMO_USERS=1`.
- Real-world forecast accuracy still depends on input quality and assumptions.
