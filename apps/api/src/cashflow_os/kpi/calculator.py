from decimal import Decimal
from statistics import mean
from typing import Dict, List

from cashflow_os.domain.models import (
    Counterparty,
    EntityType,
    EventType,
    ForecastInput,
    ForecastRun,
    KPISet,
    KPIValue,
    RelationshipType,
)
from cashflow_os.utils.money import safe_ratio


def _estimate_days(outstanding_minor_units: int, thirty_day_flow_minor_units: int) -> Decimal:
    if thirty_day_flow_minor_units <= 0:
        return Decimal("0.00")
    return safe_ratio(outstanding_minor_units * 30, thirty_day_flow_minor_units)


def _top_share(events: List, sign: int) -> Decimal:
    totals: Dict[str, int] = {}
    total_amount = 0
    for event in events:
        if sign == 1 and event.signed_minor_units <= 0:
            continue
        if sign == -1 and event.signed_minor_units >= 0:
            continue
        counterparty_name = event.counterparty_name or "Unassigned"
        amount = abs(event.signed_minor_units)
        totals[counterparty_name] = totals.get(counterparty_name, 0) + amount
        total_amount += amount
    if total_amount == 0 or not totals:
        return Decimal("0.00")
    return safe_ratio(max(totals.values()) * 100, total_amount)


def build_kpis(run: ForecastRun, forecast_input: ForecastInput) -> KPISet:
    first_day = run.daily_points[0]
    last_day = run.daily_points[-1]
    minimum_balance = min(point.closing_balance_minor_units for point in run.daily_points)

    weeks_to_shortfall = None
    for bucket in run.weekly_buckets:
        if bucket.closing_balance_minor_units < 0:
            weeks_to_shortfall = bucket.week_index
            break

    cash_in = sum(point.inflow_minor_units for point in run.daily_points)
    cash_out = sum(point.outflow_minor_units for point in run.daily_points)
    overdue_receivables = sum(
        event.net_minor_units
        for event in forecast_input.events
        if event.event_type == EventType.INFLOW
        and event.due_date
        and event.due_date < run.as_of_date
        and event.status.value in ("open", "partially_paid")
    )
    overdue_payables = sum(
        event.net_minor_units
        for event in forecast_input.events
        if event.event_type in (EventType.OUTFLOW, EventType.TAX)
        and event.due_date
        and event.due_date < run.as_of_date
        and event.status.value in ("open", "partially_paid")
    )

    thirty_day_inflows = sum(
        event.signed_minor_units
        for event in run.resolved_events
        if 0 <= (event.scheduled_date - run.as_of_date).days < 30 and event.signed_minor_units > 0
    )
    thirty_day_outflows = sum(
        abs(event.signed_minor_units)
        for event in run.resolved_events
        if 0 <= (event.scheduled_date - run.as_of_date).days < 30 and event.signed_minor_units < 0
    )

    dso = _estimate_days(overdue_receivables, thirty_day_inflows)
    dpo = _estimate_days(overdue_payables, thirty_day_outflows)
    inventory_minor_units = forecast_input.inventory_snapshot.inventory_minor_units if forecast_input.inventory_snapshot else 0
    dio = _estimate_days(inventory_minor_units, thirty_day_outflows)
    cash_conversion_cycle = (dso + dio - dpo).quantize(Decimal("0.01"))

    customer_counterparties = [cp for cp in forecast_input.counterparties if cp.relationship_type == RelationshipType.CUSTOMER]
    customer_confidences = [cp.collection_confidence for cp in customer_counterparties]
    overdue_penalty = 0
    if overdue_receivables and thirty_day_inflows:
        overdue_penalty = float(min(Decimal("25"), safe_ratio(overdue_receivables * 100, thirty_day_inflows)))
    base_confidence = (mean(customer_confidences) * 100) if customer_confidences else 72.0
    collection_reliability = max(0.0, round(base_confidence - overdue_penalty, 1))

    msme_payable_at_risk = sum(
        abs(event.signed_minor_units) for event in run.resolved_events if "msme_43b_h" in event.risk_flags
    )
    gst_next_30 = sum(
        abs(event.signed_minor_units)
        for event in run.resolved_events
        if event.entity_type == EntityType.GST and 0 <= (event.scheduled_date - run.as_of_date).days < 30
    )
    tds_next_30 = sum(
        abs(event.signed_minor_units)
        for event in run.resolved_events
        if event.entity_type == EntityType.TDS and 0 <= (event.scheduled_date - run.as_of_date).days < 30
    )
    epf_payroll_next_30 = sum(
        abs(event.signed_minor_units)
        for event in run.resolved_events
        if event.entity_type in (EntityType.EPF, EntityType.PAYROLL) and 0 <= (event.scheduled_date - run.as_of_date).days < 30
    )

    buffer = run.scenario.minimum_cash_buffer_minor_units or 0
    buffer_coverage = 0
    if buffer > 0:
        buffer_coverage = max(0, round((minimum_balance / buffer) * 100, 1))

    inventory_cover_days = Decimal(str(forecast_input.inventory_snapshot.raw_material_cover_days or 0)) if forecast_input.inventory_snapshot else Decimal("0")
    revenue_concentration = _top_share(run.resolved_events, 1)
    purchase_concentration = _top_share(run.resolved_events, -1)

    return KPISet(
        top_kpis=[
            KPIValue(key="opening_cash", label="Opening Cash", unit="money", value=first_day.opening_balance_minor_units),
            KPIValue(key="closing_cash", label="Closing Cash", unit="money", value=last_day.closing_balance_minor_units),
            KPIValue(key="minimum_cash", label="Minimum Cash", unit="money", value=minimum_balance),
            KPIValue(key="net_cash_flow", label="Net Cash Flow", unit="money", value=last_day.closing_balance_minor_units - first_day.opening_balance_minor_units),
            KPIValue(key="cash_in", label="Cash In", unit="money", value=cash_in),
            KPIValue(key="cash_out", label="Cash Out", unit="money", value=cash_out),
            KPIValue(key="weeks_to_shortfall", label="Weeks to Shortfall", unit="weeks", value=weeks_to_shortfall or 0),
            KPIValue(key="buffer_coverage", label="Buffer Coverage", unit="percent", value=buffer_coverage),
        ],
        working_capital=[
            KPIValue(key="overdue_receivables", label="Overdue Receivables", unit="money", value=overdue_receivables),
            KPIValue(key="overdue_payables", label="Overdue Payables", unit="money", value=overdue_payables),
            KPIValue(key="dso", label="DSO", unit="days", value=float(dso)),
            KPIValue(key="dpo", label="DPO", unit="days", value=float(dpo)),
            KPIValue(key="dio", label="DIO", unit="days", value=float(dio)),
            KPIValue(key="ccc", label="Cash Conversion Cycle", unit="days", value=float(cash_conversion_cycle)),
            KPIValue(key="collection_reliability", label="Collection Reliability", unit="score", value=collection_reliability),
        ],
        manufacturer=[
            KPIValue(key="inventory_cover_days", label="Inventory Cover", unit="days", value=float(inventory_cover_days)),
            KPIValue(key="revenue_concentration", label="Customer Concentration", unit="percent", value=float(revenue_concentration)),
            KPIValue(key="purchase_concentration", label="Vendor Concentration", unit="percent", value=float(purchase_concentration)),
        ],
        compliance=[
            KPIValue(key="msme_payable_at_risk", label="MSME Payable at Risk", unit="money", value=msme_payable_at_risk),
            KPIValue(key="gst_due_next_30", label="GST Due Next 30 Days", unit="money", value=gst_next_30),
            KPIValue(key="tds_due_next_30", label="TDS Due Next 30 Days", unit="money", value=tds_next_30),
            KPIValue(key="epf_payroll_due_next_30", label="EPF & Payroll Due Next 30 Days", unit="money", value=epf_payroll_next_30),
        ],
    )
