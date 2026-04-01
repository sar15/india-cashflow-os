from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from cashflow_os.domain.models import (
    CanonicalCashEvent,
    Counterparty,
    EntityType,
    EventStatus,
    EventType,
    ForecastAlert,
    ForecastScenario,
    RecurringObligation,
    ResolvedCashEvent,
    ScenarioKind,
    Severity,
)
from cashflow_os.utils.dates import clamp_day, daterange, month_sequence
from cashflow_os.utils.money import scale_minor_units


RULE_VERSION = "india-rules-v1"
CALENDAR_VERSION = "india-calendar-v1"
FORMULA_VERSION = "direct-cash-v1"

DEFAULT_DUE_DAY_BY_ENTITY = {
    EntityType.GST: 20,
    EntityType.TDS: 7,
    EntityType.EPF: 15,
    EntityType.PAYROLL: 1,
    EntityType.EMI: 5,
    EntityType.RENT: 5,
}


def default_due_day(entity_type: EntityType) -> int:
    return DEFAULT_DUE_DAY_BY_ENTITY.get(entity_type, 1)


def expand_recurring_obligations(
    org_id: str,
    as_of_date: date,
    horizon_days: int,
    obligations: List[RecurringObligation],
) -> List[CanonicalCashEvent]:
    events: List[CanonicalCashEvent] = []
    end_date = as_of_date + timedelta(days=horizon_days - 1)

    for obligation in obligations:
        due_day = obligation.due_day or default_due_day(obligation.obligation_type)
        if obligation.frequency.value == "one_time":
            scheduled_date = obligation.start_date
            if as_of_date <= scheduled_date <= end_date:
                events.append(
                    CanonicalCashEvent(
                        org_id=org_id,
                        source_id="system.recurring_obligation",
                        import_batch_id="system-generated",
                        event_type=EventType.OUTFLOW,
                        entity_type=obligation.obligation_type,
                        document_number=obligation.name,
                        document_date=scheduled_date,
                        due_date=scheduled_date,
                        expected_cash_date=scheduled_date,
                        gross_minor_units=obligation.amount_minor_units,
                        net_minor_units=obligation.amount_minor_units,
                        status=EventStatus.PLANNED,
                        source_confidence=1.0,
                        mapping_confidence=1.0,
                        notes=obligation.notes or "Generated from one-time obligation",
                        source_label=obligation.name,
                    )
                )
            continue

        if obligation.frequency.value == "weekly":
            current = max(obligation.start_date, as_of_date)
            while current <= end_date:
                events.append(
                    CanonicalCashEvent(
                        org_id=org_id,
                        source_id="system.recurring_obligation",
                        import_batch_id="system-generated",
                        event_type=EventType.OUTFLOW,
                        entity_type=obligation.obligation_type,
                        document_number="{name}-{current}".format(name=obligation.name, current=current.isoformat()),
                        document_date=current,
                        due_date=current,
                        expected_cash_date=current,
                        gross_minor_units=obligation.amount_minor_units,
                        net_minor_units=obligation.amount_minor_units,
                        status=EventStatus.PLANNED,
                        source_confidence=1.0,
                        mapping_confidence=1.0,
                        notes=obligation.notes or "Generated from weekly obligation",
                        source_label=obligation.name,
                    )
                )
                current = current + timedelta(days=7)
            continue

        months = month_sequence(as_of_date.replace(day=1), 6)
        for year, month in months:
            scheduled_date = clamp_day(year, month, due_day)
            if scheduled_date < obligation.start_date:
                continue
            if obligation.end_date and scheduled_date > obligation.end_date:
                continue
            if as_of_date <= scheduled_date <= end_date:
                events.append(
                    CanonicalCashEvent(
                        org_id=org_id,
                        source_id="system.recurring_obligation",
                        import_batch_id="system-generated",
                        event_type=EventType.OUTFLOW,
                        entity_type=obligation.obligation_type,
                        document_number="{name}-{month}".format(name=obligation.name, month=scheduled_date.strftime("%Y%m%d")),
                        document_date=scheduled_date,
                        due_date=scheduled_date,
                        expected_cash_date=scheduled_date,
                        gross_minor_units=obligation.amount_minor_units,
                        net_minor_units=obligation.amount_minor_units,
                        status=EventStatus.PLANNED,
                        source_confidence=1.0,
                        mapping_confidence=1.0,
                        notes=obligation.notes or "Generated from monthly obligation",
                        source_label=obligation.name,
                    )
                )
    return events


def resolve_event(
    event: CanonicalCashEvent,
    as_of_date: date,
    scenario: ForecastScenario,
    counterparties: Dict[str, Counterparty],
) -> Tuple[Optional[ResolvedCashEvent], List[ForecastAlert]]:
    alerts: List[ForecastAlert] = []
    if event.status in (EventStatus.PAID, EventStatus.DISPUTED):
        return None, alerts

    base_date = event.expected_cash_date or event.due_date or event.document_date
    if base_date is None:
        alerts.append(
            ForecastAlert(
                severity=Severity.WARNING,
                kind="missing_date",
                title="Missing schedule date",
                message="Event {event_id} could not be scheduled because it is missing document and due dates.".format(
                    event_id=event.document_number
                ),
                event_id=event.event_id,
            )
        )
        return None, alerts

    counterparty = counterparties.get(event.counterparty_id) if event.counterparty_id else None
    behavior_delay = counterparty.behavioral_delay_days if counterparty else 0

    scenario_delay = 0
    scalar_bps = 10000
    if event.event_type == EventType.INFLOW:
        scenario_delay = scenario.inflow_delay_days
        scalar_bps = scenario.inflow_scalar_bps
    elif event.event_type in (EventType.OUTFLOW, EventType.TAX):
        scenario_delay = scenario.outflow_delay_days
        scalar_bps = scenario.outflow_scalar_bps

    effective_date = base_date + timedelta(days=behavior_delay + scenario_delay)
    reason_parts = ["Base date {date}".format(date=base_date.isoformat())]
    if behavior_delay:
        reason_parts.append("behavioral delay {delay}d".format(delay=behavior_delay))
    if scenario_delay:
        reason_parts.append("scenario shift {delay}d".format(delay=scenario_delay))

    if effective_date < as_of_date:
        effective_date = as_of_date
        reason_parts.append("rolled into forecast day 1 because it is already overdue")

    signed_minor_units = event.net_minor_units
    if scalar_bps != 10000:
        signed_minor_units = scale_minor_units(event.net_minor_units, scalar_bps)
        reason_parts.append("amount scaled to {bps} bps".format(bps=scalar_bps))

    if event.event_type in (EventType.OUTFLOW, EventType.TAX):
        signed_minor_units *= -1

    risk_flags: List[str] = []
    if counterparty and counterparty.is_msme_registered and event.entity_type == EntityType.BILL:
        statutory_limit = event.statutory_limit_days or 45
        if event.document_date:
            limit_date = event.document_date + timedelta(days=statutory_limit)
            if effective_date > limit_date:
                risk_flags.append("msme_43b_h")
                alerts.append(
                    ForecastAlert(
                        severity=Severity.CRITICAL,
                        kind="msme_43b_h",
                        title="MSME vendor payment exceeds statutory threshold",
                        message=(
                            "Vendor {name} is marked as MSME and payment is projected after {limit} days."
                        ).format(name=counterparty.entity_name, limit=statutory_limit),
                        amount_minor_units=abs(signed_minor_units),
                        due_date=limit_date,
                        event_id=event.event_id,
                    )
                )

    resolved = ResolvedCashEvent(
        event_id=event.event_id,
        source_event_id=event.event_id,
        display_name=event.document_number,
        entity_type=event.entity_type,
        counterparty_name=event.counterparty_name or (counterparty.entity_name if counterparty else None),
        scheduled_date=effective_date,
        signed_minor_units=signed_minor_units,
        source_confidence=event.source_confidence,
        mapping_confidence=event.mapping_confidence,
        is_generated=event.source_id == "system.recurring_obligation",
        risk_flags=risk_flags,
        reason="; ".join(reason_parts),
    )
    return resolved, alerts


def build_compliance_alerts(
    resolved_events: Iterable[ResolvedCashEvent],
    as_of_date: date,
) -> List[ForecastAlert]:
    alerts: List[ForecastAlert] = []
    upcoming_window = as_of_date + timedelta(days=30)
    for event in resolved_events:
        if event.entity_type in (EntityType.GST, EntityType.TDS, EntityType.EPF, EntityType.PAYROLL, EntityType.EMI):
            if as_of_date <= event.scheduled_date <= upcoming_window:
                alerts.append(
                    ForecastAlert(
                        severity=Severity.INFO,
                        kind="compliance_due",
                        title="{label} due soon".format(label=event.entity_type.value.upper()),
                        message="{label} obligation is scheduled within the next 30 days.".format(
                            label=event.entity_type.value.upper()
                        ),
                        amount_minor_units=abs(event.signed_minor_units),
                        due_date=event.scheduled_date,
                        event_id=event.event_id,
                    )
                )
    return alerts


def standard_scenario_variants(base: ForecastScenario) -> List[ForecastScenario]:
    return [
        ForecastScenario(
            name="Base Case",
            kind=base.kind,
            description=base.description,
            inflow_delay_days=base.inflow_delay_days,
            outflow_delay_days=base.outflow_delay_days,
            inflow_scalar_bps=base.inflow_scalar_bps,
            outflow_scalar_bps=base.outflow_scalar_bps,
            opening_cash_adjustment_minor_units=base.opening_cash_adjustment_minor_units,
            minimum_cash_buffer_minor_units=base.minimum_cash_buffer_minor_units,
        ),
        ForecastScenario(
            name="Stress Case",
            kind=ScenarioKind.STRESS,
            description="Collection delays and slightly higher cash outflow pressure.",
            inflow_delay_days=base.inflow_delay_days + 7,
            outflow_delay_days=base.outflow_delay_days,
            inflow_scalar_bps=max(base.inflow_scalar_bps - 700, 8500),
            outflow_scalar_bps=base.outflow_scalar_bps + 500,
            opening_cash_adjustment_minor_units=base.opening_cash_adjustment_minor_units,
            minimum_cash_buffer_minor_units=base.minimum_cash_buffer_minor_units,
        ),
        ForecastScenario(
            name="Upside Case",
            kind=ScenarioKind.UPSIDE,
            description="Collections improve and some planned outflows slip later.",
            inflow_delay_days=max(base.inflow_delay_days - 3, 0),
            outflow_delay_days=base.outflow_delay_days + 3,
            inflow_scalar_bps=min(base.inflow_scalar_bps + 300, 11000),
            outflow_scalar_bps=max(base.outflow_scalar_bps - 200, 9000),
            opening_cash_adjustment_minor_units=base.opening_cash_adjustment_minor_units,
            minimum_cash_buffer_minor_units=base.minimum_cash_buffer_minor_units,
        ),
    ]


def build_overdue_alerts(events: List[CanonicalCashEvent], as_of_date: date) -> List[ForecastAlert]:
    alerts: List[ForecastAlert] = []
    for event in events:
        if event.status in (EventStatus.PAID, EventStatus.DISPUTED):
            continue
        if event.due_date and event.due_date < as_of_date:
            alerts.append(
                ForecastAlert(
                    severity=Severity.WARNING,
                    kind="overdue_item",
                    title="Overdue item rolled into forecast",
                    message="Document {doc} is already overdue as of the forecast date.".format(
                        doc=event.document_number
                    ),
                    amount_minor_units=event.net_minor_units,
                    due_date=event.due_date,
                    event_id=event.event_id,
                )
            )
    return alerts
