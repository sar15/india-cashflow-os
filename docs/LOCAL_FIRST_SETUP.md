# Local-First Setup

This is the recommended free path for local development on a MacBook Air or similar machine:

- `Postgres` in Docker for the future relational path
- `Redis` in Docker for future background jobs and queue work
- `MinIO` in Docker for free S3-compatible object storage
- the API and web app running directly on your machine for the fastest feedback loop

## Start the local infra

```bash
docker compose -f compose.local.yml up -d
```

The local services use development-only defaults:

- Postgres: database `cashflow_os`, user `cashflow`, password `cashflow`
- Redis: `redis://127.0.0.1:6379`
- MinIO API: `http://127.0.0.1:9000`
- MinIO console: `http://127.0.0.1:9001`
- MinIO credentials: `minioadmin` / `minioadmin`
- MinIO bucket: `cashflow-os-local`

## Run the API

```bash
cd apps/api
cp .env.example .env
python3 -m uvicorn --app-dir src cashflow_os.api.main:app --reload
```

Fastest start:

- keep `CASHFLOW_STORAGE_BACKEND=local`
- state stays in `data/cashflow-os-state.json`
- report files stay in `data/report-files`

Local object storage path:

- set `CASHFLOW_STORAGE_BACKEND=minio`
- keep the default S3 env vars from `apps/api/.env.example`
- state and report files will persist to local MinIO instead of the repo `data/` folder

## Run the web app

```bash
cd apps/web
cp .env.example .env.local
npm run dev
```

## Run the desktop sync agent

```bash
cd apps/desktop_agent
cp .env.example .env
python3 main.py
```

The desktop agent:

- registers the machine through `/v1/desktop-agents/register`
- sends heartbeats through `/v1/desktop-agents/{id}/heartbeat`
- watches a local folder with lightweight polling
- uploads new supported files through `/v1/imports`

## Gemini key

The current sync bridge and API do not require Gemini yet. Keep any Gemini key only in a local untracked env file if you want it ready for a later AI parsing step, but do not commit it into the repository.
