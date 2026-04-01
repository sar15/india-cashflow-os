# India Cashflow OS — Full Codebase Audit Report

> **Audited by**: Orchestrator + Backend Specialist + Frontend Specialist  
> **Date**: 2026-03-31  
> **Files reviewed**: 40+ source files, 14 tests (all pass), 5 source material files  
> **PRD**: [prd.md](file:///Users/sarhanak/Documents/cashflow%20projection%20/prd.md)

---

## 1. Executive Summary

The codebase implements a **solid MVP foundation** for the India Cashflow OS. The core financial engine (forecast, rules, KPIs) is well-designed with correct money handling, deterministic computation, and good audit traceability. However, there are **significant gaps** between this MVP and the production-grade system described in the PRD.

### Verdict: **Phase 0-1 MVP ≈ 55-60% of PRD Phase 1 scope**

| Dimension | Status | Details |
|-----------|--------|---------|
| Domain Model | ✅ Strong | All core types present, money in paise, enums are clean |
| Forecast Engine | ✅ Solid | Daily granularity, weekly bucketing, conservation law verified |
| India Rules Engine | ✅ Good | GST/TDS/EPF/payroll/EMI/MSME 43B(h) all present |
| KPI Layer | ✅ Complete | All 20+ KPIs from PRD implemented |
| Ingestion (Manual) | ✅ Working | Template parsing functional |
| Ingestion (Tally) | ⚠️ Basic | Parses CSV/Excel, but no XML support, no Dr/Cr smart handling |
| Ingestion (Zoho) | ⚠️ Stub | JSON payload only, no OAuth |
| API Surface | ✅ Full | All v1 endpoints present |
| Auth/RBAC | ⚠️ Token-based | Works but not production-grade (no JWT, no DB) |
| Data Layer | 🔴 **Missing** | In-memory only, no PostgreSQL |
| Queue/Workers | 🔴 **Missing** | No Redis/Celery, everything synchronous |
| PDF Export | ✅ Working | ReportLab-based, professional layout |
| Excel Export | ✅ Working | XlsxWriter with charts, formatting, audit sheet |
| Frontend | ⚠️ Scaffold | Demo-first fallback, server components, no ECharts |
| Tests | ⚠️ Basic | 14 tests pass but coverage is minimal |
| Observability | 🔴 **Missing** | No structured logging, metrics, or job traces |
| Desktop Agent | ⚠️ API seam | Registration endpoint only |

---

## 2. Architecture Cross-Check vs PRD

### PRD Spec: "Modular monolith with separate worker processes"

```
PRD Module Boundaries → Code Module Mapping

identity_and_orgs      → api/auth.py (basic token registry) ⚠️ Minimal
source_connections     → api/main.py (Zoho/Desktop routes) ✅ Present
raw_ingestion          → ingestion/service.py           ✅ Present
parsing_and_mapping    → ingestion/manual_template.py   ✅ Present
                         ingestion/tally.py              ✅ Present
                         ingestion/zoho.py               ✅ Present
canonical_finance_model → domain/models.py              ✅ Complete
rules_engine           → rules/india.py                 ✅ Complete
forecast_engine        → forecast/engine.py             ✅ Complete
kpi_engine             → kpi/calculator.py              ✅ Complete
reporting_engine       → reports/builder.py             ✅ Present
                         reports/exporters.py            ✅ Present
ai_assist              → 🔴 NOT IMPLEMENTED (expected Phase 2)
audit_and_trace        → domain/models.py (AuditTrace)  ⚠️ Model exists, no dedicated module
```

> [!IMPORTANT]
> The PRD's module boundaries are correctly reflected as Python packages. The architecture is properly layered with `domain → rules → forecast → kpi → reports`. No circular dependencies found.

### PRD Spec: "Chosen Stack"

| Stack Item | PRD | Implementation | Match |
|-----------|-----|----------------|-------|
| Frontend | Next.js + TS + React + ECharts | Next.js 15.2 + TS + React 19 | ⚠️ **No ECharts** — SVG charts inline |
| Backend | Python FastAPI monolith | FastAPI 0.121 ✅ | ✅ |
| Parsing | pandas + openpyxl + polars | pandas + openpyxl ✅ | ⚠️ No polars |
| Queue | Redis + Celery/Dramatiq | 🔴 None | 🔴 Missing |
| Database | PostgreSQL | 🔴 In-memory dict + JSON file | 🔴 Missing |
| File Storage | S3-compatible | 🔴 In-memory bytes | 🔴 Missing |
| PDF | Headless Chromium | ReportLab | ⚠️ Different approach (but works) |
| Excel | XlsxWriter/openpyxl | XlsxWriter ✅ | ✅ |
| Desktop Agent | Go Windows app | API registration seam only | ⚠️ Expected |
| Observability | Structured logs, audit trail | Basic Python logging | ⚠️ Minimal |

---

## 3. Domain Model Deep Dive

### File: [models.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/domain/models.py)

#### CanonicalCashEvent Cross-Check

| PRD Field | Implementation | Status |
|-----------|---------------|--------|
| `org_id` | ✅ `str` | ✅ |
| `source_id` | ✅ `str` | ✅ |
| `import_batch_id` | ✅ `str` | ✅ |
| `event_id` | ✅ `str` (uuid4 default) | ✅ |
| `event_type` | ✅ Enum: inflow/outflow/transfer/tax/financing/adjustment | ✅ |
| `entity_type` | ✅ Enum: invoice/bill/payroll/rent/gst/tds/epf/emi/inventory/manual/other | ✅ |
| `counterparty_id` | ✅ Optional[str] | ✅ |
| `document_number` | ✅ `str` | ✅ |
| `document_date` | ✅ Optional[date] | ✅ |
| `due_date` | ✅ Optional[date] | ✅ |
| `expected_cash_date` | ✅ Optional[date] | ✅ |
| `gross_minor_units` | ✅ `int` | ✅ |
| `tax_minor_units` | ✅ `int` default 0 | ✅ |
| `tds_minor_units` | ✅ `int` default 0 | ✅ |
| `net_minor_units` | ✅ `int` | ✅ |
| `currency` | ✅ `str` default "INR" | ✅ |
| `status` | ✅ Enum: open/partially_paid/paid/planned/disputed | ✅ |
| `source_confidence` | ✅ `float` default 1.0 | ✅ |
| `mapping_confidence` | ✅ `float` default 1.0 | ✅ |
| `rule_version` | ✅ `str` default "india-rules-v1" | ✅ |
| `forecast_inclusion_status` | ✅ Enum: included/excluded/needs_review | ✅ |

> [!TIP]
> All 20 fields from the PRD's `CanonicalCashEvent` contract are implemented with correct types and sensible defaults. The `extra="forbid"` Pydantic config prevents data leakage.

#### Other Core Types Cross-Check

| PRD Type | Code | Status |
|----------|------|--------|
| `Counterparty` | ✅ Includes MSME flag, behavioral delay, collection confidence | ✅ |
| `RecurringObligation` | ✅ With frequency enum (monthly/weekly/one_time) | ✅ |
| `BankBalanceSnapshot` | ✅ | ✅ |
| `InventorySnapshot` | ✅ With raw_material_cover_days | ✅ |
| `ForecastScenario` | ✅ With scalar_bps (basis points), delays, buffer | ✅ |
| `ForecastRun` | ✅ With all versioning metadata | ✅ |
| `KPISet` | ✅ Grouped: top/working_capital/manufacturer/compliance | ✅ |
| `ReportPack` | ✅ With charts, sections, methodology notes | ✅ |
| `AuditTrace` | ✅ | ✅ |

#### Money Storage Policy Cross-Check

| PRD Rule | Implementation | Status |
|----------|---------------|--------|
| Integer minor units (BIGINT paise) | ✅ All `*_minor_units` fields are `int` | ✅ |
| Fixed-scale decimal for ratios only | ✅ `Decimal` used in KPI calculator, `safe_ratio()` | ✅ |
| Never binary float for financials | ✅ `to_minor_units()` uses `Decimal` → `int` | ✅ |
| Format at display time only | ✅ `format_inr()` and `from_minor_units()` only in export | ✅ |

> [!NOTE]
> The money handling is **exemplary**. The [money.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/utils/money.py) module uses `Decimal` with `ROUND_HALF_UP` for conversion, `scale_minor_units` for basis-point scaling, and `parse_indian_number` handles `Dr/Cr` suffixes and `₹` symbols correctly.

---

## 4. Forecast Engine Deep Dive

### File: [engine.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/forecast/engine.py)

#### PRD Calculation Policy Cross-Check

| PRD Rule | Implementation | Status |
|----------|---------------|--------|
| Daily granularity in Asia/Kolkata | ✅ Daily loop via `daterange()` | ⚠️ No timezone awareness |
| 13-week default (91 days) | ✅ `horizon_days: int = 91` in ForecastInput | ✅ |
| Direct cash method: opening + inflows - outflows | ✅ Line 75: `running_balance = opening_balance + inflow - outflow` | ✅ |
| Store as_of_date, calendar_version, rule_version, scenario on every run | ✅ Lines 160-168 | ✅ |
| Cash shortfall warning | ✅ Lines 78-89: first negative balance triggers CRITICAL alert | ✅ |
| Cash buffer breach warning | ✅ Lines 90-103 | ✅ |
| Overdue items rolled into day 1 | ✅ `resolve_event()` in rules/india.py line 176-178 | ✅ |
| Conservation law: opening + net = closing | ✅ **Tested**: `test_cash_conservation_holds` passes | ✅ |

> [!WARNING]
> **Issue found**: The engine does NOT enforce `Asia/Kolkata` timezone. All dates are naive `date` objects. For v1 with INR-only this is acceptable, but **must be fixed before multi-currency or cross-timezone use**.

#### Scenario Engine Cross-Check

| Feature | Status |
|---------|--------|
| Base scenario | ✅ User-defined or default |
| Stress scenario auto-generation | ✅ +7 day inflow delay, -700 bps inflow, +500 bps outflow |
| Upside scenario auto-generation | ✅ -3 day inflow delay, +3 day outflow delay, +300/-200 bps |
| Scenarios share same event set | ✅ `build_standard_scenario_runs()` uses same `ForecastInput` |
| Independent forecast runs per scenario | ✅ Each gets its own `ForecastRun` |

---

## 5. Rules Engine Deep Dive

### File: [india.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/rules/india.py)

#### PRD Rules Policy Cross-Check

| PRD Rule | Implementation | Status |
|----------|---------------|--------|
| Compliance calendars are deterministic and versioned | ✅ `RULE_VERSION`, `CALENDAR_VERSION`, `FORMULA_VERSION` constants | ✅ |
| GST due day 20 | ✅ `DEFAULT_DUE_DAY_BY_ENTITY` | ✅ |
| TDS due day 7 | ✅ | ✅ |
| EPF due day 15 | ✅ | ✅ |
| Payroll due day 1 | ✅ | ✅ |
| EMI due day 5 | ✅ | ✅ |
| MSME 43B(h) 45-day threshold | ✅ Lines 189-207: checks `is_msme_registered` + date diff | ✅ |
| Incomplete data → unresolved exceptions (not silent assumptions) | ✅ Missing date → alert instead of guess | ✅ |
| Manual overrides are audit-tracked | ⚠️ Override mechanism exists via `expected_cash_date`, but not audited separately | ⚠️ |
| Paid/Disputed events excluded from forecast | ✅ Line 139: `event.status in (PAID, DISPUTED)` returns None | ✅ |

#### Recurring Obligation Expansion

- ✅ Supports `monthly`, `weekly`, `one_time` frequencies
- ✅ Uses `clamp_day()` for month-end safety (e.g., Feb 28/29)
- ✅ Generates up to 6 months of monthly obligations
- ✅ All generated events tagged as `source_id="system.recurring_obligation"`

---

## 6. KPI Layer Deep Dive

### File: [calculator.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/kpi/calculator.py)

#### PRD Required KPIs Cross-Check

| PRD KPI | Implementation Key | Status |
|---------|-------------------|--------|
| Opening cash | `opening_cash` | ✅ |
| Closing cash | `closing_cash` | ✅ |
| Minimum projected cash | `minimum_cash` | ✅ |
| Weeks to shortfall | `weeks_to_shortfall` | ✅ |
| Cash buffer coverage | `buffer_coverage` | ✅ |
| Cash in / cash out | `cash_in` / `cash_out` | ✅ |
| Net cash flow | `net_cash_flow` | ✅ |
| Overdue receivables | `overdue_receivables` | ✅ |
| Overdue payables | `overdue_payables` | ✅ |
| DSO | `dso` | ✅ |
| DPO | `dpo` | ✅ |
| DIO | `dio` | ✅ |
| Cash conversion cycle | `ccc` (DSO + DIO - DPO) | ✅ |
| Collection reliability score | `collection_reliability` | ✅ |
| MSME payable at risk | `msme_payable_at_risk` | ✅ |
| GST due next 30 days | `gst_due_next_30` | ✅ |
| TDS due next 30 days | `tds_due_next_30` | ✅ |
| EPF/payroll due next 30 days | `epf_payroll_due_next_30` | ✅ |
| Inventory cover days | `inventory_cover_days` | ✅ |
| Revenue concentration by customer | `revenue_concentration` | ✅ |
| Purchase concentration by vendor | `purchase_concentration` | ✅ |

> **All 21 PRD KPIs are implemented.** ✅

---

## 7. Reporting Engine Deep Dive

### Files: [builder.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/reports/builder.py), [exporters.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/reports/exporters.py)

#### PRD Required Report Pack Cross-Check

| PRD Section | Implementation | Status |
|-------------|---------------|--------|
| Executive summary with top 6-8 KPIs | ✅ `sections[0]` with `top_kpis[:8]` | ✅ |
| 13-week cash line/area chart | ✅ `line-area` chart | ✅ |
| Inflow vs outflow stacked bar | ✅ `stacked-bars` chart | ✅ |
| Cash bridge waterfall | ✅ `waterfall` chart | ✅ |
| AR aging heatmap | ✅ `heatmap` chart with 5 buckets | ✅ |
| AP calendar/schedule | ⚠️ No dedicated AP heatmap (only compliance timeline) | ⚠️ |
| Working capital KPI section | ✅ "Working Capital" section | ✅ |
| Manufacturer-specific section | ✅ "Manufacturer Lens" section | ✅ |
| Compliance calendar section | ✅ `timeline` chart for GST/TDS/EPF/payroll/EMI | ✅ |
| Scenario comparison section | ✅ Conditional `scenario` chart with closing/minimum | ✅ |
| Methodology and audit notes | ✅ `methodology_notes` with 4 entries | ✅ |
| Customer concentration Pareto | ✅ `pareto` chart | ✅ |
| Vendor concentration Pareto | ✅ `pareto` chart (negative events) | ✅ |

#### PRD Design Rules Cross-Check

| PRD Design Rule | Status | Notes |
|----------------|--------|-------|
| Indian currency formatting by default | ✅ | `format_inr()` with lakh grouping |
| One narrative per page | ✅ | Each section has a `narrative` field |
| Every chart has explaining subtitle | ✅ | All `ChartSpec` have `subtitle` |
| PDF and Excel must match web numbers | ⚠️ | Same data source, but rounding paths differ slightly |

> [!IMPORTANT]
> **PDF uses ReportLab (programmatic), not Headless Chromium (HTML-rendered)**. The PRD mentions headless Chromium for "server-rendered HTML templates." The current ReportLab approach Works™ but produces a less visually rich PDF than browser-rendered HTML. This is a deliberate v1 trade-off.

---

## 8. Ingestion Layer Deep Dive

### PRD Ingestion Precedence Cross-Check

| PRD Step | Implementation | Status |
|----------|---------------|--------|
| 1. Deterministic parser by source type | ✅ `parse_import()` routes by SourceType | ✅ |
| 2. Source-specific mapping dictionary & heuristics | ✅ Tally uses `PARTY_HEADERS`, `AMOUNT_HEADERS`, etc. | ✅ |
| 3. AI parser fallback below confidence threshold | 🔴 Not implemented (architecture seam only) | Expected |
| 4. User review for unresolved exceptions only | ✅ `ImportIssue` model, `unresolved_issues` tracked | ✅ |

#### Tally Parser Issues

- ⚠️ **No XML parsing** — PRD mentions "Tally XML/HTTP" but only CSV/Excel supported
- ⚠️ **No merged-cell handling** — PRD explicitly calls out "merged cells" in messy Tally exports
- ⚠️ **No shifted-header detection** — PRD mentions "shifted headers"
- ✅ Indian number parsing with Dr/Cr handling
- ✅ Flexible header matching (multiple synonyms)

#### Zoho Parser Issues

- ✅ Handles `invoices` and `bills` arrays from payload
- ⚠️ No OAuth token exchange — JSON payload ingestion only
- ⚠️ No `contacts`, `payments`, or bank balance extraction from Zoho
- ⚠️ `date` fields from Zoho passed as-is (no parsing/validation)

---

## 9. API Surface Cross-Check

| PRD Endpoint | Implementation | Status |
|-------------|---------------|--------|
| `POST /v1/imports` | ✅ File upload + JSON body + demo mode | ✅ |
| `GET /v1/imports/{id}` | ✅ | ✅ |
| `POST /v1/imports/{id}/confirm-mapping` | ✅ | ✅ |
| `POST /v1/sources/zoho/connect` | ✅ | ✅ |
| `POST /v1/desktop-agents/register` | ✅ | ✅ |
| `POST /v1/obligations` | ✅ | ✅ |
| `POST /v1/scenarios` | ✅ | ✅ |
| `POST /v1/forecast-runs` | ✅ | ✅ |
| `GET /v1/forecast-runs/{id}` | ✅ | ✅ |
| `GET /v1/dashboards/cash?org_id=...&scenario_id=...` | ✅ | ✅ |
| `POST /v1/reports` | ✅ | ✅ |
| `GET /v1/reports/{id}/download?format=pdf\|xlsx` | ✅ | ✅ |
| `GET /v1/audit/trace?forecast_run_id=...&event_id=...` | ✅ | ✅ |

> **All 13 PRD endpoints are implemented.** ✅

#### Auth/RBAC Cross-Check

| PRD Role | Implementation | Status |
|----------|---------------|--------|
| Owner | ✅ `demo-owner-token` | ✅ |
| Finance Manager | ✅ `demo-finance-token` | ✅ |
| Accountant | ✅ `demo-accountant-token` | ✅ |
| Viewer | ✅ `demo-viewer-token` | ✅ |
| Role enforcement on endpoints | ✅ `require_roles()` + `ensure_org_access()` | ✅ |

> [!WARNING]
> Auth is **token-registry-based**, not JWT/session-based. Acceptable for MVP but needs proper auth (e.g., Supabase Auth, Auth0) for production.

---

## 10. Frontend Cross-Check

### Architecture

| Feature | Status | Notes |
|---------|--------|-------|
| Next.js App Router | ✅ | Using React 19, server components |
| 4-step flow (Connect → Review → Rules → Forecast) | ✅ | Pages: `/imports`, `/setup`, `/dashboard` |
| Professional dashboard | ✅ | KPI grid, charts, alerts, compliance timeline |
| PDF/Excel download buttons | ✅ | BFF routes proxy to backend |
| Demo mode fallback | ✅ | Hardcoded `demoPayload` when API unavailable |
| ECharts integration | 🔴 | **Not used** — custom inline SVG charts instead |
| Responsive layout | ✅ | CSS media query at 1100px breakpoint |

### BFF (Backend-for-Frontend) Routes

| Route | Purpose | Status |
|-------|---------|--------|
| `/api/imports` (POST) | Proxy file upload to FastAPI | ✅ |
| `/api/onboarding/complete` (POST) | Orchestrates confirm-mapping + forecast-run | ✅ |
| `/api/reports/[format]` (GET) | Creates report pack + downloads PDF/XLSX | ✅ |

> [!NOTE]
> The BFF pattern is well-executed. The Next.js routes handle the multi-step orchestration (confirm → run → download) and unit conversion (INR → minor units) cleanly.

### CSS Design System

The [globals.css](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/web/app/globals.css) uses:
- ✅ Warm, professional palette (cream bg, teal brand, coral accent)
- ✅ Glassmorphism cards (`backdrop-filter: blur(16px)`)
- ✅ Premium typography (Iowan Old Style for headings)
- ✅ Consistent design tokens (custom properties)
- ⚠️ No dark mode
- ⚠️ No animations/transitions on cards (only nav-link hover)

---

## 11. Test Coverage Audit

### Current Test Files

| Test File | Tests | What's Covered |
|-----------|-------|----------------|
| [test_api.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/tests/test_api.py) | 9 | Health, auth, dashboard, RBAC, report export, state persistence |
| [test_forecast_engine.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/tests/test_forecast_engine.py) | 4 | 13-week horizon, conservation law, MSME flag, KPI build |
| [test_store.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/tests/test_store.py) | 1 | Store persistence across instances |
| **Total** | **14** | All pass ✅ |

### PRD Test Plan — Gap Analysis

| PRD Test Category | Status | Missing Tests |
|-------------------|--------|--------------|
| Golden dataset tests | 🔴 | No manually-audited reference datasets |
| Deterministic reconciliation (dashboard=PDF=Excel) | 🔴 | No cross-surface reconciliation test |
| Money precision (paise, taxes, partial payments, rounding) | ⚠️ | Only conservation law tested |
| Property tests for conservation | ✅ | `test_cash_conservation_holds` |
| Rule-version reproducibility | 🔴 | Not tested |
| Tally messy exports (merged cells, Dr/Cr, blank rows) | 🔴 | No parser edge-case tests |
| Duplicate uploads / idempotency | 🔴 | Not tested |
| Manufacturing SME scenario | ⚠️ | Demo uses manufacturing data but no domain scenario verification |
| MSME 43B(h) crossing 45-day | ✅ | `test_flags_msme_vendor_risk` |
| Visual regression (PDF/dashboard) | 🔴 | No visual tests |
| Excel structure tests | 🔴 | Only byte length checked |
| 50K events performance | 🔴 | No perf test |
| PDF under 30s | 🔴 | No timing test |
| RBAC tests | ✅ | `test_viewer_cannot_create_import` |
| Audit trail immutability | 🔴 | Not tested |

---

## 12. Source Material Review

The `/source material` directory contains **5 reference files**:
1. `Dabur_Cash_Flow.xlsx` — Real-world cash flow statement reference
2. `cashflow1.pdf`, `cashflow2.pdf`, `cashflow3.pdf` — Cash flow report templates/examples
3. `detailed_cashflow_forecast.xlsx` — Detailed forecast spreadsheet reference

These serve as **design inspiration** for the reporting output format. The current ReportLab PDF and XlsxWriter exports should be cross-referenced against these for format quality.

---

## 13. Critical Issues for Production Readiness

### 🔴 P0 — Blockers

| # | Issue | Impact | PRD Reference |
|---|-------|--------|---------------|
| 1 | **No persistent database** — everything in-memory + JSON file | Data loss on restart, no multi-instance support, no concurrent access safety | "PostgreSQL" in stack |
| 2 | **No queue/worker system** — all processing synchronous | Import of 50K events blocks the API thread, no background jobs | "Redis + Celery" in stack |
| 3 | **No file storage** — report files in memory only | Report files lost on restart, memory grows unbounded | "S3-compatible object storage" |
| 4 | **`datetime.utcnow()` is deprecated** (Python 3.12+) | Multiple instances across [models.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/domain/models.py) lines 199, 222, 343, 358 | Correctness concern |

### ⚠️ P1 — Important

| # | Issue | Impact |
|---|-------|--------|
| 5 | **No timezone awareness** — `Asia/Kolkata` in PRD, naive dates in code | Compliance dates could be wrong near midnight |
| 6 | **Tally XML parsing not supported** — only CSV/Excel | Major gap for real-world Tally users |
| 7 | **No AI parsing fallback** — architecture seam but no LLM connection | PRD allows this for v1 but Phase 2 expectation |
| 8 | **No ECharts on frontend** — inline SVG charts are functional but not interactive | PRD specifies ECharts |
| 9 | **Test coverage ~15%** — 14 tests for ~2,500 LOC | Far below PRD's test plan requirements |
| 10 | **No input validation on Tally/Zoho date fields** — passed raw from dataframe | Could crash with malformed dates |

### ⚠️ P2 — Nice to Have for v1

| # | Issue | Impact |
|---|-------|--------|
| 11 | AP due calendar heatmap missing from report pack | PRD lists it |
| 12 | No Inventory days trend chart | PRD lists it |
| 13 | No KPI sparklines | PRD lists it |
| 14 | No "click-through or trace metadata" on charts | PRD requires chart→event drill-down |
| 15 | No checksum/deduplication on imports | PRD mentions "checksum/idempotency" |
| 16 | Excel export doesn't include formula locks | PRD mentions "formula lock tests" |

---

## 14. Code Quality Observations

### ✅ Things Done Well

1. **Money handling is correct** — Decimal-based, no floating point for money, paise storage
2. **Pydantic v2 used correctly** — `extra="forbid"`, proper `Field(default_factory=...)` 
3. **Deterministic engine** — No random elements, versioned rules, reproducible outputs
4. **Clean separation of concerns** — domain/rules/forecast/kpi/reports layers are independent
5. **Audit trail built in** — Every resolved event generates an `AuditTrace` entry
6. **Indian number parsing** — Handles ₹, commas, Dr/Cr suffixes correctly
7. **INR formatting** — Proper lakh/crore grouping (e.g., ₹12,00,000.00)
8. **CORS configuration** — Environment-driven allowed origins
9. **Thread-safe state persistence** — Lock + atomic rename pattern in store
10. **BFF pattern** — Next.js routes properly orchestrate multi-step API flows

### ⚠️ Issues Found in Code

1. **`datetime.utcnow()`** used at lines 199, 222, 343, 358 in models.py — deprecated since Python 3.12, use `datetime.now(timezone.utc)` instead
2. **No `.env` file** — API_BASE_URL must be set manually for frontend-backend connection; no documentation for this
3. **Demo data values in `demo-data.ts`** are in INR (not paise) — this is correct for display but inconsistent naming (`value: 1800000` looks like paise)
4. **`report_files` dict in `InMemoryStore`** is NOT persisted to JSON — report exports are lost on restart
5. **No `requirements.txt`** — only `pyproject.toml` with declared deps; no lockfile
6. **`weekly_buckets` can panic** if `horizon_days` is 0 — `bucket_points[0]` would IndexError
7. **`_aging_buckets()` calculates age as `(as_of_date - scheduled_date).days`** — this gives negative values for future dates, meaning most events land in "0-15" bucket incorrectly

---

## 15. PRD Delivery Plan vs Actual Progress

```
Phase 0 (weeks 1-2): Domain glossary, KPI dictionary, formula registry, schema
  → ✅ COMPLETE (models.py, calculator.py, rules/india.py)

Phase 1 (weeks 3-8): Monolith, uploads, parsers, dashboard, PDF/Excel
  → ⚠️ ~60% COMPLETE
     ✅ Modular monolith foundation
     ✅ Uploads and raw import batches
     ✅ Manual template parser, Tally parser, Zoho parser (basic)
     ✅ Opening cash, obligations, direct forecast engine
     ✅ Weekly dashboard with KPIs
     ✅ PDF and Excel report generation
     ✅ GST/TDS/EPF/payroll/EMI rules and alerting
     🔴 No PostgreSQL database
     🔴 No Celery/Redis workers
     🔴 No mapping UI (just API endpoint)
     ⚠️ Basic test coverage

Phase 2 (weeks 9-14): Not started
Phase 3 (weeks 15-24): Not started
Phase 4 (after PMF): Not started
```

---

## 16. Source Material → Codebase Alignment

The 5 source material files (Dabur cash flow, 3 PDF reports, 1 detailed forecast Excel) serve as **design references**. The current implementation:

- ✅ Generates similar KPI-driven executive summaries
- ✅ Produces 13-week cash flow projections matching the forecast spreadsheet structure
- ⚠️ PDF visual quality is below the reference PDFs (programmatic ReportLab vs designed PDFs)
- ⚠️ Excel output lacks the polish of the `detailed_cashflow_forecast.xlsx` reference

---

## 17. Recommendations — Prioritized Roadmap

### 🔴 Immediate (before any user testing)

1. **Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`** — 4 instances
2. **Add PostgreSQL** (even SQLite for local dev) to replace in-memory store
3. **Fix `_aging_buckets()` logic** — future events should not use `as_of_date - scheduled_date`
4. **Add edge-case guard** for empty `weekly_buckets` / `daily_points`

### ⚠️ Short-term (Phase 1 completion)

5. Add Celery/Redis for background import processing
6. Add proper JWT/session auth (replace token registry)
7. Integrate ECharts on frontend for interactive charts
8. Add golden dataset tests and reconciliation tests
9. Add Tally XML parsing support
10. Persist report files to filesystem/S3

### 📋 Medium-term (Phase 2)

11. Zoho OAuth connector
12. AI parsing fallback (LLM integration)
13. Full test suite per PRD test plan
14. Performance testing with 50K events
15. Accountant collaboration roles

---

> [!CAUTION]
> The PRD ends with: **"make project fully production that contain zero errors"**. The current codebase is a **well-architected MVP foundation** but is **not production-ready**. The primary gaps are infrastructure (no DB, no queue, no file storage) and test coverage. The financial math is the strongest part of the implementation.
