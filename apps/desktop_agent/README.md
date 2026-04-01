# Desktop Sync Agent

Lightweight local folder watcher for the existing Cashflow OS API.

## What it does

- registers the current machine with the API
- sends periodic heartbeats so the backend knows the machine is online
- watches a local export folder with simple polling
- uploads new files to `/v1/imports`
- tags uploads with the desktop agent id so the API can track the latest sync activity

## Quick start

```bash
cd apps/desktop_agent
cp .env.example .env
python3 main.py
```

For a single dry-run pass:

```bash
python3 main.py --once
```

## Supported files

- `.xlsx`
- `.xls`
- `.csv`
- `.xml`

`DESKTOP_AGENT_SOURCE_TYPE=auto` uses simple file-name heuristics:

- `.xml` defaults to `tally`
- names with `tally`, `receivable`, `payable`, `debtor`, `creditor`, or `ledger` default to `tally`
- everything else defaults to `manual`

`DESKTOP_AGENT_SOURCE_HINT=auto` defaults to:

- `payables` for names containing `payable`, `creditor`, or `vendor`
- `receivables` otherwise
