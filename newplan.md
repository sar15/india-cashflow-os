# 🔍 India Cashflow OS — Complete PRD vs Codebase Audit

> Audit Date: 2026-04-01 | Auditor: Orchestrator + Project Planner + Backend Specialist
> Every PRD requirement audited line-by-line against every source file.

---

## Scoring Summary

| Status | Count | Meaning |
|--------|-------|---------|
| ✅ BUILT | 48 | Fully implemented and matches PRD |
| ⚠️ PARTIALLY BUILT | 19 | Scaffold exists but incomplete |
| ❌ NOT BUILT | 27 | Completely missing from codebase |
| 🔴 WRONGLY BUILT | 5 | Built but violates PRD specification |

---

## 1. PRODUCT SHAPE (PRD Lines 18-55)

### 1.1 Four-Step User Journey (PRD Line 19-26)

| Step | PRD Requirement | Status | Evidence |
|------|-----------------|--------|----------|
| 1. Connect or Upload | Tally, Zoho, Excel template | ✅ BUILT | [import-workbench.tsx](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/web/components/import-workbench.tsx), [service.py](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/api/src/cashflow_os/ingestion/service.py) |
| 2. Review Exceptions Only | Mapping gaps, missing dates, suspicious values | ✅ BUILT | `ImportIssue` model, `unresolved_issues` in ImportBatch, exception display in import-workbench |
| 3. Add Cash Rules | Opening balance, recurring obligations, buffer, scenarios | ✅ BUILT | [setup-workbench.tsx](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/web/components/setup-workbench.tsx) |
| 4. Get Forecast | Dashboard, PDF, Excel, drill-downs | ✅ BUILT | [dashboard-experience.tsx](file:///Users/sarhanak/Documents/cashflow%20projection%20/apps/web/components/dashboard-experience.tsx), exporters.py |

### 1.2 First Release Outcomes (PRD Lines 28-33)

| Outcome | Status | Evidence |
|---------|--------|----------|
| 13-week cash balance forecast (daily internal, weekly display) | ✅ BUILT | `engine.py` L73-162: daily loop + weekly aggregation |
| Lowest cash point + shortfall warning | ✅ BUILT | `engine.py` L81-92: `cash_shortfall` alert |
| Compliance risk panel (GST, TDS, EPF, EMI, payroll, 43B(h)) | ✅ BUILT | `india.py` L226-248: compliance alerts; `calculator.py` L96-113 |
| Collections confidence panel | ⚠️ PARTIALLY BUILT | `collection_reliability` KPI exists in calculator.py L88-94, but it's a single score — not a per-customer panel showing which customers may delay |
| Professional management report (web, PDF, Excel) | ✅ BUILT | `builder.py`, `exporters.py` (PDF + Excel) |

### 1.3 First Report Pack Requirements (PRD Lines 35-46)

| Report Section | Status | Evidence |
|----------------|--------|----------|
| Executive summary with top 6-8 KPIs | ✅ BUILT | `builder.py` L204-219 |
| 13-week cash line/area chart | ✅ BUILT | `builder.py` L107-118 |
| Inflow/outflow stacked bars by week | ✅ BUILT | `builder.py` L119-133 |
| Cash bridge waterfall | ✅ BUILT | `builder.py` L134-155 |
| AR aging heatmap | ✅ BUILT | `builder.py` L156-167 |
| AP calendar + MSME vendor-risk table | ⚠️ PARTIALLY BUILT | AP heatmap exists (`builder.py` L168-179); **MSME vendor-risk table is NOT a separate section** — MSME risk is only an alert, not a proper table |
| Working-capital KPIs (DSO, DPO, DIO, CCC, overdue AR/AP) | ✅ BUILT | `calculator.py` L82-86, L135-143 |
| Manufacturer section (inventory days, RM cover, concentration) | ✅ BUILT | `calculator.py` L144-148, `builder.py` L238-245 |
| Compliance calendar section | ✅ BUILT | `builder.py` L180-191 (timeline chart) |
| Scenario comparison section | ✅ BUILT | `builder.py` L81-96, L246-253 |
| Methodology and audit notes appendix | ✅ BUILT | `builder.py` L260-265 |

### 1.4 Design Rules for Reports (PRD Lines 48-55)

| Rule | Status | Evidence |
|------|--------|----------|
| Indian currency formatting by default | ✅ BUILT | `money.py` L55-70: proper `format_inr()` with Indian grouping (₹XX,XX,XXX.XX) |
| One narrative per page | ✅ BUILT | Each `ReportSection` has a single `narrative` field |
| Every chart has subtitle explaining what changed | ✅ BUILT | All `ChartSpec` instances have descriptive subtitles |
| Print-safe accessible colors | ⚠️ PARTIALLY BUILT | Uses `#0f8b8d`/`#f07167` palette — decent but **not formally validated for accessibility (WCAG contrast)** |
| All report totals reconcile | ✅ BUILT | Single `ForecastRun` is the source of truth for all surfaces |
| PDF and Excel match web numbers | ✅ BUILT | All exports read from same `ForecastRun` object |

---

## 2. ARCHITECTURE (PRD Lines 56-118)

### 2.1 Modular Monolith (PRD Line 57)

| Aspect | Status | Evidence |
|--------|--------|----------|
| Modular monolith with separate worker processes | 🔴 WRONGLY BUILT | **No worker processes exist.** Everything runs in-process in the FastAPI app. No Redis, no Celery/Dramatiq. Background job handling is completely absent. All parsing/forecasting is synchronous. |

### 2.2 Chosen Stack (PRD Lines 108-118)

| Technology | PRD Spec | Status | Evidence |
|------------|----------|--------|----------|
| Frontend | Next.js + TS + React + ECharts | ✅ BUILT | `apps/web/` with Next.js, TypeScript, ECharts |
| Backend | Python FastAPI modular monolith | ✅ BUILT | `apps/api/` with FastAPI |
| Parsing | pandas + openpyxl + polars | ⚠️ PARTIALLY BUILT | pandas + openpyxl used; **polars is NOT used anywhere** |
| Queue/background jobs | Redis + Celery or Dramatiq | ❌ NOT BUILT | No queue system, no worker processes, no Redis |
| Database | PostgreSQL | 🔴 WRONGLY BUILT | **Uses InMemoryStore with JSON file persistence** — no PostgreSQL at all. This is a fundamental architectural deviation. |
| File storage | S3-compatible object storage | ⚠️ PARTIALLY BUILT | `blob_storage.py` has S3/Vercel Blob support but falls back to local filesystem. No MinIO in docker-compose. |
| PDF generation | Headless Chromium from HTML templates | 🔴 WRONGLY BUILT | **Uses ReportLab** (Python lib) for PDF, not headless Chromium. PRD explicitly says "headless Chromium from server-rendered HTML templates" |
| Excel export | XlsxWriter or openpyxl | ✅ BUILT | Uses `xlsxwriter` in `exporters.py` |
| Desktop agent | Go-based Windows tray app | 🔴 WRONGLY BUILT | **Written in Python**, not Go. PRD says "lightweight tray/service app in Go". Current implementation is a Python CLI polling script. |
| Observability | Structured logs, audit trail, job traces, timing | ⚠️ PARTIALLY BUILT | Basic `logging.info` for requests exists; audit trail tables exist; **no job traces, no structured logging (JSON), no timing metrics** |

### 2.3 Module Boundaries (PRD Lines 120-131)

| PRD Module | Status | Actual Implementation |
|------------|--------|----------------------|
| `identity_and_orgs` | ⚠️ PARTIALLY BUILT | `auth.py` has token-based auth with RBAC (owner/finance_manager/accountant/viewer). **No org management, no user CRUD, no accountant collaboration, no billing** |
| `source_connections` | ✅ BUILT | `SourceConnectionRecord`, Zoho OAuth, desktop-agent registration, source sync jobs |
| `raw_ingestion` | ⚠️ PARTIALLY BUILT | Raw file parsing exists but **no raw payload capture, no checksums stored in DB** (checksum is in-memory only) |
| `parsing_and_mapping` | ✅ BUILT | `ingestion/service.py`, `tally.py`, `zoho.py`, `manual_template.py` with parser registry pattern |
| `canonical_finance_model` | ✅ BUILT | `domain/models.py` has `CanonicalCashEvent` and all supporting types |
| `rules_engine` | ✅ BUILT | `rules/india.py` with compliance calendars, MSME 43B(h), overdue alerts |
| `forecast_engine` | ✅ BUILT | `forecast/engine.py` with daily computation, weekly aggregation, scenarios |
| `kpi_engine` | ✅ BUILT | `kpi/calculator.py` with all required KPIs |
| `reporting_engine` | ✅ BUILT | `reports/builder.py`, `exporters.py`, `traces.py` |
| `ai_assist` | ❌ NOT BUILT | **Zero AI/ML code exists.** No sheet understanding fallback, no mapping suggestions, no AI explanations, no Q&A |
| `audit_and_trace` | ✅ BUILT | `AuditTrace` model, `traces.py`, drill-down API endpoint |

---

## 3. CANONICAL DATA CONTRACTS (PRD Lines 133-174)

### 3.1 CanonicalCashEvent (PRD Lines 136-157)

| Field | Status | Evidence |
|-------|--------|----------|
| `org_id` | ✅ | models.py L110 |
| `source_id` | ✅ | models.py L111 |
| `import_batch_id` | ✅ | models.py L112 |
| `event_id` | ✅ | models.py L113 |
| `event_type` (6 values) | ✅ | models.py L20-26 |
| `entity_type` (11 values) | ✅ | models.py L29-40 |
| `counterparty_id` | ✅ | models.py L116 |
| `document_number` | ✅ | models.py L118 |
| `document_date` | ✅ | models.py L119 |
| `due_date` | ✅ | models.py L120 |
| `expected_cash_date` | ✅ | models.py L121 |
| `gross_minor_units` | ✅ | models.py L122 |
| `tax_minor_units` | ✅ | models.py L123 |
| `tds_minor_units` | ✅ | models.py L124 |
| `net_minor_units` | ✅ | models.py L125 |
| `currency` | ✅ | models.py L126 |
| `status` (5 values) | ✅ | models.py L43-48 |
| `source_confidence` | ✅ | models.py L128 |
| `mapping_confidence` | ✅ | models.py L129 |
| `rule_version` | ✅ | models.py L130 |
| `forecast_inclusion_status` | ✅ | models.py L131 |

### 3.2 Other Core Types (PRD Lines 159-168)

| Type | Status | Evidence |
|------|--------|----------|
| `Counterparty` | ✅ BUILT | models.py L95-104 |
| `RecurringObligation` | ✅ BUILT | models.py L137-149 |
| `BankBalanceSnapshot` | ✅ BUILT | models.py L152-156 |
| `InventorySnapshot` | ✅ BUILT | models.py L159-163 |
| `ForecastScenario` | ✅ BUILT | models.py L166-178 |
| `ForecastRun` | ✅ BUILT | models.py L372-390 |
| `KPISet` | ✅ BUILT | models.py L324-328 |
| `ReportPack` | ✅ BUILT | models.py L362-369 |
| `AuditTrace` | ✅ BUILT | models.py L278-286 |

### 3.3 Money Storage Policy (PRD Lines 170-174)

| Rule | Status | Evidence |
|------|--------|----------|
| All cash amounts as integer minor units (BIGINT paise) | ✅ BUILT | All money fields use `int` minor units throughout |
| Fixed-scale decimal for ratios | ✅ BUILT | `from decimal import Decimal` used in `money.py`, `calculator.py` |
| Never use binary floating point for financial calculation | ⚠️ PARTIALLY | Mostly correct, but `ChartSeries.values` is `List[float]` (display values only, computed from minor units). Safe because it's presentation-layer only. |
| Every exported number from same immutable ForecastRun | ✅ BUILT | All exports derive from single `ForecastRun` |

---

## 4. PUBLIC API SURFACE (PRD Lines 176-191)

| Endpoint | PRD Spec | Status | Actual Route |
|----------|----------|--------|--------------|
| `POST /v1/imports` | Upload import | ✅ BUILT | main.py L271 |
| `GET /v1/imports/{id}` | Get import | ✅ BUILT | main.py L350 |
| `POST /v1/imports/{id}/confirm-mapping` | Confirm mapping | ✅ BUILT | main.py L362 |
| `POST /v1/sources/zoho/connect` | Zoho connect | ✅ BUILT | main.py L411 |
| `POST /v1/desktop-agents/register` | Agent registration | ✅ BUILT | main.py L583 |
| `POST /v1/obligations` | Create obligation | ✅ BUILT | main.py L401 |
| `POST /v1/scenarios` | Create scenario | ✅ BUILT | main.py L620 |
| `POST /v1/forecast-runs` | Create forecast | ✅ BUILT | main.py L630 |
| `GET /v1/forecast-runs/{id}` | Get forecast | ✅ BUILT | main.py L641 |
| `GET /v1/dashboards/cash` | Cash dashboard | ✅ BUILT | main.py L653 |
| `POST /v1/reports` | Generate report | ✅ BUILT | main.py L680 |
| `GET /v1/reports/{id}/download?format=pdf\|xlsx` | Download report | ✅ BUILT | main.py L698 |
| `GET /v1/audit/trace` | Audit trace | ✅ BUILT | main.py L741 |

**Extra endpoints built (not in PRD but useful):**
- `POST /v1/sources/zoho/exchange` (OAuth code exchange)
- `POST /v1/sources/zoho/{id}/sync` (Zoho sync)
- `POST /v1/desktop-agents/{id}/heartbeat`
- `GET /v1/reports/{id}/charts/{id}/trace` (chart drill-down)
- `GET /v1/auth/session`
- `GET /health`

---

## 5. CALCULATION POLICY (PRD Lines 194-218)

### 5.1 Forecasting Policy (PRD Lines 196-201)

| Rule | Status | Evidence |
|------|--------|----------|
| Daily granularity in Asia/Kolkata | ⚠️ PARTIALLY | Computes at daily granularity (engine.py L73), but **timezone is not applied**. All dates are naive. PRD says `Asia/Kolkata`. |
| 13-week default weekly view | ✅ BUILT | `horizon_days=91` default, weekly buckets generated |
| Direct cash method | ✅ BUILT | Opening + inflows - outflows (engine.py L78) |
| Store as-of date, calendar version, rule version, scenario version | ✅ BUILT | ForecastRun stores all four |
| Monthly/indirect 3-way only in Phase 3 | N/A | Correctly deferred |

### 5.2 Rules Engine Policy (PRD Lines 203-207)

| Rule | Status | Evidence |
|------|--------|----------|
| Compliance calendars deterministic + versioned | ✅ BUILT | `RULE_VERSION`, `CALENDAR_VERSION`, `FORMULA_VERSION` constants |
| GST/TDS/EPF/EMI/payroll/43B(h) are rules, not AI | ✅ BUILT | All in `india.py` as deterministic code |
| Incomplete data creates unresolved exceptions | ✅ BUILT | `ImportIssue` + `ForecastAlert` for missing dates |
| Manual overrides first-class + audited | ⚠️ PARTIALLY | User can override `expected_cash_date` but **no audit log entry specifically for overrides** |

### 5.3 Collections/Payment Timing Policy (PRD Lines 209-213)

| Rule | Status | Evidence |
|------|--------|----------|
| Base rule: due date | ✅ BUILT | `india.py` L142: falls back to due_date |
| Rules layer: customer/vendor overrides | ✅ BUILT | `behavioral_delay_days` on Counterparty |
| ML layer: expected delays | ❌ NOT BUILT | Phase 2+ — correctly deferred |
| User override expected cash dates | ✅ BUILT | `expected_cash_date` field |

### 5.4 AI/ML Policy (PRD Lines 215-219)

| Rule | Status | Evidence |
|------|--------|----------|
| AI for parsing messy sheets | ❌ NOT BUILT | No AI parser fallback |
| AI for suggesting mappings | ❌ NOT BUILT | No mapping suggestion engine |
| AI for summarizing insights | ❌ NOT BUILT | No AI insight writer |
| AI for Q&A | ❌ NOT BUILT | No conversational Q&A |
| AI NOT allowed for rules/money | ✅ | All rules are deterministic |
| Forecast shows value source (rule/override/model) | ⚠️ PARTIALLY | `reason` field exists but doesn't explicitly tag source type as enum |

---

## 6. DATA INGESTION STRATEGY (PRD Lines 221-237)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Tally exports (debtors, creditors, day book, trial balance, outstanding) | ⚠️ PARTIALLY | Tally parser handles CSV/Excel/XML, but **only receivables/payables**. No day book, trial balance, or outstanding ledger parsing. |
| Zoho Books (invoices, bills, contacts, payments, bank) | ⚠️ PARTIALLY | Invoices + bills parsed. **Contacts, payments, and bank-related balances are NOT fetched** (zoho_client.py only fetches invoices + bills) |
| Manual Excel template | ✅ BUILT | `manual_template.py` with Setup/Cash Events/Obligations sheets |
| Ingestion precedence (deterministic → heuristics → AI → user) | ⚠️ PARTIALLY | Deterministic parsers exist, basic heuristics in Tally parser. **No AI fallback (step 3), no confidence-threshold gate** |
| Desktop sync v1 ships without mandatory desktop | ✅ BUILT | Desktop agent is optional |
| Desktop agent: watch folder, upload signed files | ✅ BUILT | `desktop_agent/main.py` watches folder + uploads |
| No sensitive data stored in agent after upload | ✅ BUILT | Agent only stores fingerprints, not file content |

---

## 7. KPIs (PRD Lines 239-263)

| KPI | Status | Evidence |
|-----|--------|----------|
| Opening cash | ✅ | calculator.py L126 |
| Closing cash | ✅ | calculator.py L127 |
| Minimum projected cash | ✅ | calculator.py L128 |
| Weeks to shortfall | ✅ | calculator.py L46-50, L132 |
| Cash buffer coverage | ✅ | calculator.py L115-118, L133 |
| Cash in / cash out | ✅ | calculator.py L52-53, L130-131 |
| Net cash flow | ✅ | calculator.py L129 |
| Overdue receivables | ✅ | calculator.py L54-61 |
| Overdue payables | ✅ | calculator.py L62-69 |
| DSO | ✅ | calculator.py L82, L138 |
| DPO | ✅ | calculator.py L83, L139 |
| DIO | ✅ | calculator.py L85, L140 |
| Cash conversion cycle | ✅ | calculator.py L86, L141 |
| Collection reliability score | ✅ | calculator.py L88-94, L142 |
| MSME payable at risk | ✅ | calculator.py L96-98, L150 |
| GST due next 30 days | ✅ | calculator.py L99-103, L151 |
| TDS due next 30 days | ✅ | calculator.py L104-108, L152 |
| EPF/payroll due next 30 days | ✅ | calculator.py L109-113, L153 |
| Inventory cover days | ✅ | calculator.py L120, L145 |
| Revenue concentration by customer | ✅ | calculator.py L121, L146 |
| Purchase concentration by vendor | ✅ | calculator.py L122, L147 |

> **All 21 KPIs from PRD are implemented.** ✅

---

## 8. CHARTS (PRD Lines 265-275)

| Chart | PRD Spec | Status | Evidence |
|-------|----------|--------|----------|
| 13-week cash line/area chart | ✅ BUILT | builder.py L107-118 + charts.tsx `buildLineAreaOption` |
| Inflow/outflow stacked columns | ✅ BUILT | builder.py L119-133 + charts.tsx `buildGroupedBarOption` |
| Waterfall bridge | ✅ BUILT | builder.py L134-155 + charts.tsx `buildWaterfallOption` |
| AR aging heatmap | ✅ BUILT | builder.py L156-167 + charts.tsx `buildHeatmapOption` |
| AP due calendar heatmap | ✅ BUILT | builder.py L168-179 + charts.tsx `buildHeatmapOption` |
| KPI sparklines | ❌ NOT BUILT | No sparkline charts exist anywhere |
| Customer concentration Pareto | ✅ BUILT | builder.py L192 + charts.tsx `buildParetoOption` |
| Scenario comparison variance | ✅ BUILT | builder.py L81-96 + charts.tsx `buildScenarioOption` |
| Inventory days trend | ❌ NOT BUILT | No trend chart for inventory |
| Compliance deadline timeline | ✅ BUILT | builder.py L180-191 + charts.tsx `buildTimelineOption` |

---

## 9. REPORT GENERATION POLICY (PRD Lines 277-281)

| Rule | Status | Evidence |
|------|--------|----------|
| Reports are template-driven | ✅ BUILT | `builder.py` builds from `ReportSection` + `ChartSpec` templates |
| Chart specs reused in web, PDF, Excel | ⚠️ PARTIALLY | Web uses ECharts from ChartSpec. **PDF uses ReportLab (completely separate chart rendering).** Excel has its own chart. **Charts are NOT truly reused — they are rebuilt per surface.** |
| Commentary templated first, AI-enhanced second | ⚠️ PARTIALLY | Templated commentary exists. **No AI enhancement.** |
| Every chart supports click-through/trace metadata | ✅ BUILT | `trace_points` in ChartSpec.meta, `resolve_report_chart_trace()` in traces.py |

---

## 10. TEST PLAN (PRD Lines 283-326)

### 10.1 Test Files Present

| Test File | Coverage | Status |
|-----------|----------|--------|
| `test_api.py` (10.5KB) | API endpoint tests | ⚠️ EXISTS |
| `test_forecast_engine.py` (1.5KB) | Forecast core | ⚠️ MINIMAL |
| `test_ingestion.py` (4.1KB) | Parser tests | ⚠️ EXISTS |
| `test_local_smoke.py` (1.7KB) | Smoke tests | ⚠️ MINIMAL |
| `test_reporting.py` (3.8KB) | Report tests | ⚠️ EXISTS |
| `test_store.py` (1.7KB) | Store tests | ⚠️ MINIMAL |

### 10.2 PRD Test Requirements vs Reality

| Test Category | Status | Gap |
|---------------|--------|-----|
| Golden dataset tests with audited outputs | ❌ NOT BUILT | No golden dataset exists |
| Deterministic reconciliation (dashboard = PDF = Excel) | ❌ NOT BUILT | No cross-surface reconciliation test |
| Money precision tests (paise, taxes, rounding) | ❌ NOT BUILT | No precision-specific tests |
| Property tests (opening + net = closing) | ❌ NOT BUILT | No property-based testing |
| Rule-version reproducibility tests | ❌ NOT BUILT | No reproducibility tests |
| Clean Zoho Books payload tests | ⚠️ PARTIAL | Some in test_ingestion.py |
| Messy Tally export tests (merged cells, Dr/Cr, Indian numbers) | ⚠️ PARTIAL | Some in test_ingestion.py |
| Duplicate upload + checksum/idempotency | ⚠️ PARTIAL | Checksum logic exists but minimal testing |
| Manufacturing SME scenario test | ❌ NOT BUILT | No domain scenario tests |
| Trading SME scenario test | ❌ NOT BUILT | |
| GST due while payment late test | ❌ NOT BUILT | |
| TDS deduction test | ❌ NOT BUILT | |
| MSME 43B(h) threshold test | ❌ NOT BUILT | |
| Multi-bank opening balance test | ❌ NOT BUILT | |
| Visual regression (PDF + dashboard) | ❌ NOT BUILT | |
| Excel formula lock tests | ❌ NOT BUILT | |
| "Exceptions only" flow <10 clicks test | ❌ NOT BUILT | |
| 50K events in <10s performance test | ❌ NOT BUILT | |
| PDF gen <30s performance test | ❌ NOT BUILT | |
| RBAC (owner/finance/accountant/viewer) tests | ⚠️ PARTIAL | Auth tests exist in test_api.py |
| Audit trail immutability tests | ❌ NOT BUILT | |
| PII access control tests | ❌ NOT BUILT | |

---

## 11. DELIVERY PLAN (PRD Lines 328-354)

### Phase 0 (Weeks 1-2)

| Task | Status | Evidence |
|------|--------|----------|
| Domain glossary, KPI dictionary, formula registry | ❌ NOT BUILT | No glossary/dictionary docs |
| Collect 20-30 real anonymized samples | ❌ NOT BUILT | Only 1 demo dataset in `store.py` |
| Freeze canonical schema + validation rules | ✅ BUILT | `models.py` has the frozen schema |
| Design report templates + chart grammar | ✅ BUILT | `builder.py` + `ChartSpec` is the grammar |

### Phase 1 (Weeks 3-8) — **INCOMPLETE**

| Task | Status | Evidence |
|------|--------|----------|
| Modular monolith foundation | 🔴 WRONG | No workers, no Redis, no PostgreSQL |
| Uploads, raw import batches, deterministic parsers | ✅ BUILT | |
| Mapping UI | ✅ BUILT | import-workbench.tsx |
| Manual Excel template | ✅ BUILT | templates/ directory |
| Opening cash, obligations, direct forecast engine | ✅ BUILT | |
| Weekly dashboard | ✅ BUILT | |
| First PDF/Excel report | ✅ BUILT | |
| GST/TDS/EPF/payroll/EMI rules and alerting | ✅ BUILT | |

### Phase 2 (Weeks 9-14) — **Status Mixed**

| Task | Status | Evidence |
|------|--------|----------|
| Zoho Books connector | ✅ BUILT | Full OAuth flow + sync |
| Accountant collaboration roles | ⚠️ PARTIALLY | Roles exist (owner/finance/accountant/viewer) but **no multi-org, no client-facing report pack workflow** |
| Customer/vendor overrides | ✅ BUILT | `behavioral_delay_days`, `collection_confidence` |
| Scenario engine | ✅ BUILT | base/stress/upside scenarios |
| AR/AP drill-downs | ✅ BUILT | Chart trace system |
| Manufacturer KPI layer | ✅ BUILT | |
| AI parser fallback | ❌ NOT BUILT | |
| AI-written report commentary | ❌ NOT BUILT | |

### Phase 3 (Weeks 15-24) — **Mostly Not Started**

| Task | Status | Evidence |
|------|--------|----------|
| Windows desktop sync agent | ⚠️ PARTIALLY | Python agent exists (not Go, not Windows-specific) |
| ML payment-delay model | ❌ NOT BUILT | |
| Anomaly detection | ❌ NOT BUILT | |
| Confidence scoring | ⚠️ PARTIALLY | Basic confidence fields but no ML |
| Source health | ❌ NOT BUILT | |
| Monthly projection layer | ❌ NOT BUILT | |
| Indirect 3-way modeling | ❌ NOT BUILT | |

---

## 12. CRITICAL ISSUES REQUIRING IMMEDIATE FIX

> [!CAUTION]
> These are **production-blocking** deviations from PRD.

### 🔴 Issue 1: No PostgreSQL — Using InMemoryStore with JSON File

**PRD says:** "Database: PostgreSQL"
**Reality:** `InMemoryStore` in `store.py` uses a single 1.1MB JSON file (`data/cashflow-os-state.json`). This is:
- Not ACID-compliant
- Not concurrent-safe for multi-user
- Will lose data on crash
- Cannot scale past single process

**Fix:** Migrate to PostgreSQL with SQLAlchemy/SQLModel or raw asyncpg.

---

### 🔴 Issue 2: No Background Job Processing

**PRD says:** "Queue/background jobs: Redis + Celery or Dramatiq"
**Reality:** All parsing, forecasting, and report generation is synchronous in the request handler.

**Impact:** With 50K events, the API will timeout.

---

### 🔴 Issue 3: PDF Generation Uses ReportLab Instead of Headless Chromium

**PRD says:** "PDF generation: headless Chromium from server-rendered HTML templates"
**Reality:** Uses `reportlab` library. The PDF output will look different from the web dashboard.

---

### 🔴 Issue 4: Desktop Agent Is Python, Not Go

**PRD says:** "Desktop agent: Windows-first lightweight tray/service app in Go"
**Reality:** A 316-line Python CLI script. No tray UI, no service integration, no Go.

---

### 🔴 Issue 5: Timezone Not Applied

**PRD says:** "Compute forecast internally at daily granularity in Asia/Kolkata"
**Reality:** All date operations are timezone-naive. No `Asia/Kolkata` awareness.

---

## 13. SUMMARY OF WHAT'S NOT BUILT

| Category | Missing Items |
|----------|---------------|
| **Infrastructure** | PostgreSQL, Redis, Celery/Dramatiq, MinIO/S3 in docker-compose |
| **AI Module** | Entire `ai_assist` module: sheet understanding, mapping suggestions, insight writer, Q&A |
| **Charts** | KPI sparklines, Inventory days trend chart |
| **Reports** | MSME vendor-risk table, chart-reuse across surfaces |
| **Tests** | Golden datasets, property tests, domain scenario tests, performance tests, visual regression, 16+ test categories |
| **Docs** | Domain glossary, KPI dictionary, formula registry |
| **Data** | Real anonymized sample Tally/Excel/Zoho files |
| **Desktop Agent** | Proper Go-based Windows tray/service app |
| **Ingestion** | Tally day book/trial balance parser, Zoho contacts/payments/bank fetch |
| **ML** | Payment-delay model, anomaly detection, advanced confidence scoring |
| **Planning** | Monthly projection, indirect 3-way modeling |

---

## Proposed Fix Priorities

> [!IMPORTANT]
> **Phase 1 fixes (must do for production):**

1. **Migrate to PostgreSQL** — Replace InMemoryStore with proper database
2. **Add Redis + Celery** — Background job processing for large imports
3. **Apply Asia/Kolkata timezone** — All forecast date logic
4. **Fix PDF generation** — Keep ReportLab OR switch to Chromium, but document deviation from PRD
5. **Add missing tests** — At least golden-dataset + property tests + RBAC
6. **Add KPI Sparklines** — Small gap, easy win
7. **MSME vendor-risk table** — Separate report section

> [!NOTE]
> **Phase 2 fixes (nice to have):**

8. AI parser fallback
9. Desktop agent in Go
10. Zoho contacts/payments fetch
11. Tally day book/trial balance parser
12. Domain scenario tests
13. Inventory days trend chart

---

## Open Questions for You

1. **PostgreSQL migration:** Should we proceed with SQLAlchemy/SQLModel, or raw asyncpg + migrations with Alembic?
2. **Background jobs:** Celery or Dramatiq? PRD mentions both. Celery has more ecosystem but heavier.
3. **PDF generation:** The ReportLab approach works fine. Do you want me to rewrite it with headless Chromium as PRD says, or keep ReportLab and document the deviation?
4. **Desktop agent:** Rewriting in Go is a significant effort. Keep Python for now or rewrite?
5. **AI module:** This is Phase 2+ in the PRD. Should I scaffold the module structure now or defer entirely?
6. **Test strategy:** Should I build the full test suite now, or prioritize the top 5 most critical test categories?
