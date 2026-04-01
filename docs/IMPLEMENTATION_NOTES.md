# Implementation Notes

This codebase implements the first delivery slice of the architecture plan:

- Modular monolith backend in Python/FastAPI.
- App Router frontend in Next.js.
- Deterministic direct-method cash forecast at daily granularity, summarized weekly.
- File-backed persistent repository for local durability while keeping API contracts stable.
- Checksum-based import deduplication and disk-backed report-file caching for safer local operations.
- Role-based API authentication for owner, finance manager, accountant, and viewer access.
- Live onboarding flow from import to forecast creation in the Next.js app.

## Architecture: Manual-Upload-Only Ingestion

All data enters the system via file uploads through `POST /v1/imports`. The ingestion pipeline supports three source types:

| Source Type | File Formats | Parser |
|---|---|---|
| `manual` | XLSX, CSV | `ingestion/parsers/manual_template.py` |
| `tally` | CSV, XML, XLSX | `ingestion/parsers/tally_export.py` |
| `zoho` | JSON | `ingestion/parsers/zoho_export.py` |

Parser errors are raised as `FileParseError` with row-number, column, and human-readable message context. The API layer catches these and returns structured HTTP 400 responses.

File uploads are validated before parsing:
- **50 MB** maximum file size (HTTP 413 if exceeded)
- Extension-based type checking: `.csv`, `.xlsx`, `.xls`, `.xml`, `.json` (HTTP 415 if rejected)
- Raw file bytes are held in memory only — never written to disk

MSME detection for counterparty enrichment is available in `utils/msme.py` and works on contact metadata from file exports.

## Deliberate v1 limits

- AI parsing fallback is represented as an architecture seam, not connected to an LLM in this slice.
- No background worker deployment yet; report and forecast jobs execute inline in the app process.

## Why this slice

The workspace started without an application codebase, so this pass prioritizes:

1. Correct financial domain model
2. Forecasting engine and rule layer
3. Contract-stable API
4. Professional dashboard/report shell
5. Testable foundation for the next implementation passes
