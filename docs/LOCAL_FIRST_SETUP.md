# Local-First Setup

This is the recommended free path for local development on a MacBook Air or similar machine:

- `Postgres` and `Redis` in Docker for future scale paths
- The API backend powered by local SQLite file storage for immediate portability
- The Next.js web app running directly on your machine for the fastest frontend feedback loop

## Start the local infra

```bash
docker compose -f compose.local.yml up -d
```

The local services use development-only defaults, currently providing Postgres and Redis should you opt to deploy background jobs later.

## Run the API

```bash
cd apps/api
cp .env.example .env
python3 -m uvicorn --app-dir src cashflow_os.api.main:app --reload
```

Fastest start:
- SQLAlchemy will cleanly instantiate `cashflow-os.db` in `apps/api/data/cashflow-os.db`
- API state persists there locally, so restarts won't blow away configurations.
- Generated PDF and XLSX exports will fall comfortably into `data/report-files`.

## Run the web app

```bash
cd apps/web
cp .env.example .env.local
npm run dev
```

## Desktop Agent Status

_Note: The desktop app agent previously included in this repo for automated sync has been decommissioned. Ingestions are constrained strictly to web uploads._

## Gemini key

The current sync bridge and API do not require Gemini yet. Keep any Gemini key only in a local untracked env file if you want it ready for a later AI parsing step, but do not commit it into the repository.
