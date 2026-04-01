# Implementation Notes

This codebase implements the first delivery slice of the architecture plan:

- Modular monolith backend in Python/FastAPI.
- App Router frontend in Next.js.
- Deterministic direct-method cash forecast at daily granularity, summarized weekly.
- File-backed persistent repository for local durability while keeping API contracts stable.
- Checksum-based import deduplication and disk-backed report-file caching for safer local operations.
- Role-based API authentication for owner, finance manager, accountant, and viewer access.
- Live onboarding flow from import to forecast creation in the Next.js app.

## Deliberate v1 limits

- No PostgreSQL/Redis/object-storage infrastructure yet; persistence is local file-backed state.
- Zoho integration supports JSON payload ingestion, not live OAuth token exchange.
- Tally ingestion focuses on exported ledgers and outstanding reports, not always-on sync.
- AI parsing fallback is represented as an architecture seam, not connected to an LLM in this slice.
- No background worker deployment yet; report and forecast jobs execute inline in the app process.

## Why this slice

The workspace started without an application codebase, so this pass prioritizes:

1. Correct financial domain model
2. Forecasting engine and rule layer
3. Contract-stable API
4. Professional dashboard/report shell
5. Testable foundation for the next implementation passes
