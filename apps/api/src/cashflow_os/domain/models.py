from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RelationshipType(str, Enum):
    CUSTOMER = "customer"
    VENDOR = "vendor"
    INTERNAL = "internal"
    OTHER = "other"


class EventType(str, Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    TRANSFER = "transfer"
    TAX = "tax"
    FINANCING = "financing"
    ADJUSTMENT = "adjustment"


class EntityType(str, Enum):
    INVOICE = "invoice"
    BILL = "bill"
    PAYROLL = "payroll"
    RENT = "rent"
    GST = "gst"
    TDS = "tds"
    EPF = "epf"
    EMI = "emi"
    INVENTORY = "inventory"
    MANUAL = "manual"
    OTHER = "other"


class EventStatus(str, Enum):
    OPEN = "open"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    PLANNED = "planned"
    DISPUTED = "disputed"


class ForecastInclusionStatus(str, Enum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    NEEDS_REVIEW = "needs_review"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SourceType(str, Enum):
    TALLY_EXPORT = "tally"
    ZOHO_EXPORT = "zoho"
    MANUAL = "manual"
    DEMO = "demo"


class ObligationFrequency(str, Enum):
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    ONE_TIME = "one_time"


class ScenarioKind(str, Enum):
    BASE = "base"
    STRESS = "stress"
    UPSIDE = "upside"
    CUSTOM = "custom"


class Counterparty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counterparty_id: str = Field(default_factory=lambda: str(uuid4()))
    entity_name: str
    relationship_type: RelationshipType
    is_msme_registered: bool = False
    behavioral_delay_days: int = 0
    collection_confidence: float = 0.65
    tags: List[str] = Field(default_factory=list)


class CanonicalCashEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str
    source_id: str
    import_batch_id: str
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    entity_type: EntityType
    counterparty_id: Optional[str] = None
    counterparty_name: Optional[str] = None
    document_number: str
    document_date: Optional[date] = None
    due_date: Optional[date] = None
    expected_cash_date: Optional[date] = None
    gross_minor_units: int
    tax_minor_units: int = 0
    tds_minor_units: int = 0
    net_minor_units: int
    currency: str = "INR"
    status: EventStatus = EventStatus.OPEN
    source_confidence: float = 1.0
    mapping_confidence: float = 1.0
    rule_version: str = "india-rules-v1"
    forecast_inclusion_status: ForecastInclusionStatus = ForecastInclusionStatus.INCLUDED
    notes: Optional[str] = None
    statutory_limit_days: Optional[int] = None
    source_label: Optional[str] = None


class RecurringObligation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_id: str = Field(default_factory=lambda: str(uuid4()))
    org_id: str
    name: str
    obligation_type: EntityType
    frequency: ObligationFrequency = ObligationFrequency.MONTHLY
    amount_minor_units: int
    due_day: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None


class BankBalanceSnapshot(BaseModel):
    org_id: str
    as_of_date: date
    account_name: str = "Primary Operating Account"
    balance_minor_units: int


class InventorySnapshot(BaseModel):
    org_id: str
    as_of_date: date
    inventory_minor_units: int
    raw_material_cover_days: Optional[int] = None


class ForecastScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    kind: ScenarioKind = ScenarioKind.CUSTOM
    description: Optional[str] = None
    inflow_delay_days: int = 0
    outflow_delay_days: int = 0
    inflow_scalar_bps: int = 10000
    outflow_scalar_bps: int = 10000
    opening_cash_adjustment_minor_units: int = 0
    minimum_cash_buffer_minor_units: int = 0


class OrganizationProfile(BaseModel):
    org_id: str
    company_name: str
    industry: str = "Manufacturing"
    reporting_currency: str = "INR"
    reporting_timezone: str = "Asia/Kolkata"
    fiscal_year_start_month: int = 4


class ImportIssue(BaseModel):
    issue_id: str = Field(default_factory=lambda: str(uuid4()))
    code: str
    severity: Severity
    message: str
    field_name: Optional[str] = None
    row_number: Optional[int] = None


class ImportBatch(BaseModel):
    import_batch_id: str = Field(default_factory=lambda: str(uuid4()))
    org_id: str
    source_type: SourceType
    filename: str
    created_at: datetime = Field(default_factory=utc_now)
    checksum: Optional[str] = None
    event_count: int = 0
    counterparty_count: int = 0
    obligation_count: int = 0
    unresolved_issues: List[ImportIssue] = Field(default_factory=list)





class ParsedImportBundle(BaseModel):
    import_batch: ImportBatch
    bank_balance: Optional[BankBalanceSnapshot] = None
    inventory_snapshot: Optional[InventorySnapshot] = None
    counterparties: List[Counterparty] = Field(default_factory=list)
    events: List[CanonicalCashEvent] = Field(default_factory=list)
    obligations: List[RecurringObligation] = Field(default_factory=list)


class ResolvedCashEvent(BaseModel):
    event_id: str
    display_name: str
    source_event_id: str
    entity_type: EntityType
    counterparty_name: Optional[str] = None
    scheduled_date: date
    signed_minor_units: int
    source_confidence: float
    mapping_confidence: float
    is_generated: bool = False
    risk_flags: List[str] = Field(default_factory=list)
    reason: str


class ForecastAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    severity: Severity
    kind: str
    title: str
    message: str
    amount_minor_units: Optional[int] = None
    due_date: Optional[date] = None
    event_id: Optional[str] = None


class AuditTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    event_id: str
    subject: str
    explanation: str
    effective_date: Optional[date] = None
    bucket_label: Optional[str] = None
    signed_minor_units: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DailyForecastPoint(BaseModel):
    date: date
    opening_balance_minor_units: int
    inflow_minor_units: int
    outflow_minor_units: int
    net_movement_minor_units: int
    closing_balance_minor_units: int
    event_ids: List[str] = Field(default_factory=list)
    alert_ids: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0


class WeeklyForecastBucket(BaseModel):
    week_index: int
    label: str
    start_date: date
    end_date: date
    opening_balance_minor_units: int
    inflow_minor_units: int
    outflow_minor_units: int
    net_movement_minor_units: int
    closing_balance_minor_units: int
    minimum_balance_minor_units: int
    event_ids: List[str] = Field(default_factory=list)


class KPIValue(BaseModel):
    key: str
    label: str
    unit: str
    value: Any
    description: Optional[str] = None
    status: Optional[str] = None


class KPISet(BaseModel):
    top_kpis: List[KPIValue] = Field(default_factory=list)
    working_capital: List[KPIValue] = Field(default_factory=list)
    manufacturer: List[KPIValue] = Field(default_factory=list)
    compliance: List[KPIValue] = Field(default_factory=list)


class ChartSeries(BaseModel):
    name: str
    values: List[float]
    kind: str = "line"


class ChartSpec(BaseModel):
    chart_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: str
    title: str
    subtitle: str
    x_axis: List[str]
    series: List[ChartSeries]
    meta: Dict[str, Any] = Field(default_factory=dict)


class ChartTracePoint(BaseModel):
    key: str
    label: str
    event_ids: List[str] = Field(default_factory=list)
    summary: Optional[str] = None


class ReportSection(BaseModel):
    section_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    narrative: str
    chart_ids: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)


class ReportPack(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    forecast_run_id: str
    title: str
    generated_at: datetime = Field(default_factory=utc_now)
    charts: List[ChartSpec] = Field(default_factory=list)
    sections: List[ReportSection] = Field(default_factory=list)
    methodology_notes: List[str] = Field(default_factory=list)
    sparklines: Dict[str, str] = Field(default_factory=dict)


class ForecastRun(BaseModel):
    forecast_run_id: str = Field(default_factory=lambda: str(uuid4()))
    org_id: str
    profile: OrganizationProfile
    as_of_date: date
    horizon_days: int
    calendar_version: str
    rule_version: str
    formula_version: str
    generated_at: datetime = Field(default_factory=utc_now)
    scenario: ForecastScenario
    opening_balance_minor_units: int
    resolved_events: List[ResolvedCashEvent] = Field(default_factory=list)
    daily_points: List[DailyForecastPoint] = Field(default_factory=list)
    weekly_buckets: List[WeeklyForecastBucket] = Field(default_factory=list)
    alerts: List[ForecastAlert] = Field(default_factory=list)
    kpis: Optional[KPISet] = None
    audit_trace: List[AuditTrace] = Field(default_factory=list)
    unresolved_issues: List[ImportIssue] = Field(default_factory=list)


class ForecastInput(BaseModel):
    profile: OrganizationProfile
    as_of_date: date
    opening_balance: BankBalanceSnapshot
    inventory_snapshot: Optional[InventorySnapshot] = None
    counterparties: List[Counterparty] = Field(default_factory=list)
    events: List[CanonicalCashEvent] = Field(default_factory=list)
    obligations: List[RecurringObligation] = Field(default_factory=list)
    scenario: ForecastScenario = Field(
        default_factory=lambda: ForecastScenario(
            name="Base Case",
            kind=ScenarioKind.BASE,
            description="User-entered base assumptions.",
        )
    )
    horizon_days: int = Field(default=91, ge=1)


class ReportRequest(BaseModel):
    forecast_run_id: str
    include_scenarios: bool = True


class DashboardResponse(BaseModel):
    forecast_run: ForecastRun
    report_pack: ReportPack


class ChartTraceTotals(BaseModel):
    event_count: int = 0
    trace_count: int = 0
    inflow_minor_units: int = 0
    outflow_minor_units: int = 0
    net_minor_units: int = 0


class ChartTraceResponse(BaseModel):
    report_id: str
    chart_id: str
    chart_title: str
    chart_kind: str
    trace_subject: str
    point_key: Optional[str] = None
    point_label: Optional[str] = None
    summary: str
    totals: ChartTraceTotals = Field(default_factory=ChartTraceTotals)
    events: List[ResolvedCashEvent] = Field(default_factory=list)
    traces: List[AuditTrace] = Field(default_factory=list)
