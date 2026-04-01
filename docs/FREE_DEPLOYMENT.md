# Free Deployment Guide

This repo can be deployed on free Vercel tiers or Render with persistent storage.

## Recommended layout

Deploy `apps/api` as one service (Render or Vercel):

- Root directory: `apps/api`
- Runtime entrypoint: `index.py` (Vercel) or uvicorn (Render)
- Enable Blob storage or Supabase for persistence

Deploy `apps/web` as a second project (Vercel):

- Root directory: `apps/web`
- Point `API_BASE_URL` at the deployed API URL

## API environment variables

- `DATABASE_URL=postgresql://...` (Supabase connection string)
- `CASHFLOW_ALLOWED_ORIGINS=<your web app URL>`
- `CASHFLOW_DISABLE_DEMO_AUTH=1`
- `CASHFLOW_AUTH_TOKENS_JSON=<generated token registry>`

## Web environment variables

- `API_BASE_URL=https://<your-api-domain>`
- `CASHFLOW_SESSION_SECRET=<generated session secret>`
- `CASHFLOW_DISABLE_DEMO_USERS=1`
- `CASHFLOW_WEB_USERS_JSON=<generated user registry>`

## Generate deploy-safe auth config

Run:

```bash
node scripts/generate_auth_bundle.mjs --email owner@company.com --name "Owner" --password "choose-a-strong-password" --org demo-org --role owner
```

The script prints:

- `CASHFLOW_SESSION_SECRET`
- `CASHFLOW_WEB_USERS_JSON`
- `CASHFLOW_AUTH_TOKENS_JSON`

Paste those into your hosting environment variables.
