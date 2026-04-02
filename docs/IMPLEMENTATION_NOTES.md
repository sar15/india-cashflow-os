# Implementation Notes

This codebase implements the core, un-bloated delivery slice of the cash forecasting architecture:

- Modular monolith backend in Python/FastAPI.
- App Router frontend in Next.js geared solely around a brutally simple onboarding MVP.
- Deterministic direct-method cash forecast at daily granularity, summarized weekly.
- SQLite-backed persistent repository (`cashflow_os.db`) utilizing SQLAlchemy to assure durability and cross-restart consistency.
- Checksum-based import deduplication and disk-backed file caching for robust local file handling.
- Timezone-locked (Asia/Kolkata) bounds applied to financial logic to avert date shifts.
- Role-based API authentication for owner, finance manager, accountant, and viewer access.

## Architecture: Manual-Upload MVP

All data enters the system via file uploads through `POST /v1/imports` handled by our MVP frontend. Discontinued connections such as Zoho or the Desktop agent have been fully expunged. The ingestion pipeline supports two immediate source types:

| Source Type | File Formats | Parser |
|---|---|---|
| `manual` | XLSX, CSV | `ingestion/parsers/manual_template.py` |
| `tally` | CSV, XML, XLSX | `ingestion/parsers/tally_export.py` |

Parser errors are raised as `FileParseError` with row-number, column, and human-readable message context. The API layer catches these and returns structured HTTP 400 responses.

File uploads are validated before parsing:
- **50 MB** maximum file size (HTTP 413 if exceeded)
- Extension-based type checking: `.csv`, `.xlsx`, `.xls`, `.xml`, `.json` (HTTP 415 if rejected)
- Raw file bytes are primarily held in memory for transient operations

MSME detection for counterparty enrichment is available in `utils/msme.py` and works on contact metadata from file exports.

## Deliberate MVP limits

- Complex schema mapping and dynamic scenarios have been shelved to limit scope creep — focusing explicitly on resolving "Exception Rows."
- AI parsing fallback is represented as an architecture seam, not connected to an LLM in this slice.
- Desktop Windows agent and external API syncing have been completely pruned for absolute reliability in a tight scope.

## Why this slice

This foundation guarantees exactly three things:
1. Correct financial domain model (paise-based accounting to zero exceptions).
2. Bulletproof 13-week forecast engine relying heavily on manual inputs and Tally outputs.
3. Stable, SQLite-backed architecture ready for cloud elevation.
