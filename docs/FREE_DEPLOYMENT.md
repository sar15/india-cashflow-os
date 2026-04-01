# Free Deployment Guide

This repo can now be deployed on free Vercel tiers with persistent storage and without public demo credentials.

## Recommended layout

Deploy `apps/api` as one Vercel project:

- Root directory: `apps/api`
- Runtime entrypoint: `index.py`
- Enable Blob storage on the project

Deploy `apps/web` as a second Vercel project:

- Root directory: `apps/web`
- Point `API_BASE_URL` at the deployed API URL

## API environment variables

- `CASHFLOW_STORAGE_BACKEND=vercel_blob`
- `BLOB_READ_WRITE_TOKEN=<created automatically by Vercel Blob>`
- `CASHFLOW_DISABLE_DEMO_AUTH=1`
- `CASHFLOW_AUTH_TOKENS_JSON=<generated token registry>`
- `CASHFLOW_ALLOWED_ORIGINS=<your web app URL>`
- `ZOHO_CLIENT_ID=<from Zoho API console>`
- `ZOHO_CLIENT_SECRET=<from Zoho API console>`
- `ZOHO_REDIRECT_URI=https://<your-web-app-domain>/auth/zoho/callback`

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

Paste those into the two Vercel projects.

## Zoho setup

Create a Zoho OAuth client and set the redirect URI to:

```text
https://<your-web-app-domain>/auth/zoho/callback
```

The web app now redirects users into Zoho, returns through the callback route, exchanges the code through the API, and immediately syncs invoices and bills into a new import batch.
