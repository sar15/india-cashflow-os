from datetime import timedelta
from typing import Dict, List

from cashflow_os.domain.models import (
    AuditTrace,
    DailyForecastPoint,
    ForecastAlert,
    ForecastInput,
    ForecastRun,
    ForecastScenario,
    Severity,
    WeeklyForecastBucket,
)
from cashflow_os.kpi.calculator import build_kpis
from cashflow_os.rules.india import (
    CALENDAR_VERSION,
    FORMULA_VERSION,
    RULE_VERSION,
    build_compliance_alerts,
    build_overdue_alerts,
    expand_recurring_obligations,
    resolve_event,
    standard_scenario_variants,
)
from cashflow_os.utils.dates import daterange, seven_day_windows, today_ist


def build_forecast_run(forecast_input: ForecastInput, scenario: ForecastScenario = None) -> ForecastRun:
    if forecast_input.horizon_days < 1:
        raise ValueError("Forecast horizon must be at least 1 day.")

    active_scenario = scenario or forecast_input.scenario
    counterparties = {counterparty.counterparty_id: counterparty for counterparty in forecast_input.counterparties}
    generated_events = expand_recurring_obligations(
        org_id=forecast_input.profile.org_id,
        as_of_date=forecast_input.as_of_date,
        horizon_days=forecast_input.horizon_days,
        obligations=forecast_input.obligations,
    )

    alerts: List[ForecastAlert] = []
    alerts.extend(build_overdue_alerts(forecast_input.events, forecast_input.as_of_date))

    resolved_events = []
    for event in list(forecast_input.events) + generated_events:
        resolved, event_alerts = resolve_event(
            event=event,
            as_of_date=forecast_input.as_of_date,
            scenario=active_scenario,
            counterparties=counterparties,
        )
        alerts.extend(event_alerts)
        if resolved is not None:
            resolved_events.append(resolved)

    resolved_events.sort(key=lambda item: item.scheduled_date)
    alerts.extend(build_compliance_alerts(resolved_events, forecast_input.as_of_date))

    events_by_date: Dict = {}
    for event in resolved_events:
        events_by_date.setdefault(event.scheduled_date, []).append(event)

    start_date = forecast_input.as_of_date
    end_date = forecast_input.as_of_date + timedelta(days=forecast_input.horizon_days - 1)
    running_balance = forecast_input.opening_balance.balance_minor_units + active_scenario.opening_cash_adjustment_minor_units

    audit_trace: List[AuditTrace] = []
    daily_points: List[DailyForecastPoint] = []
    first_negative_alert_added = False
    first_buffer_alert_added = False
    buffer_amount = active_scenario.minimum_cash_buffer_minor_units

    for current_date in daterange(start_date, end_date):
        opening_balance = running_balance
        day_events = events_by_date.get(current_date, [])
        inflow = sum(item.signed_minor_units for item in day_events if item.signed_minor_units > 0)
        outflow = sum(abs(item.signed_minor_units) for item in day_events if item.signed_minor_units < 0)
        running_balance = opening_balance + inflow - outflow

        day_alert_ids: List[str] = []
        if running_balance < 0 and not first_negative_alert_added:
            alert = ForecastAlert(
                severity=Severity.CRITICAL,
                kind="cash_shortfall",
                title="Projected cash shortfall",
                message="Cash balance turns negative on {date} under the active scenario.".format(date=current_date.isoformat()),
                amount_minor_units=abs(running_balance),
                due_date=current_date,
            )
            alerts.append(alert)
            day_alert_ids.append(alert.alert_id)
            first_negative_alert_added = True
        if buffer_amount and running_balance < buffer_amount and not first_buffer_alert_added:
            alert = ForecastAlert(
                severity=Severity.WARNING,
                kind="buffer_breach",
                title="Cash buffer breached",
                message="Projected balance drops below the configured cash buffer on {date}.".format(
                    date=current_date.isoformat()
                ),
                amount_minor_units=buffer_amount - running_balance,
                due_date=current_date,
            )
            alerts.append(alert)
            day_alert_ids.append(alert.alert_id)
            first_buffer_alert_added = True

        confidence = 1.0
        if day_events:
            confidence = round(
                sum((event.source_confidence + event.mapping_confidence) / 2 for event in day_events) / len(day_events),
                2,
            )

        daily_points.append(
            DailyForecastPoint(
                date=current_date,
                opening_balance_minor_units=opening_balance,
                inflow_minor_units=inflow,
                outflow_minor_units=outflow,
                net_movement_minor_units=inflow - outflow,
                closing_balance_minor_units=running_balance,
                event_ids=[event.event_id for event in day_events],
                alert_ids=day_alert_ids,
                confidence_score=confidence,
            )
        )

        for event in day_events:
            audit_trace.append(
                AuditTrace(
                    event_id=event.event_id,
                    subject="daily_forecast",
                    explanation=event.reason,
                    effective_date=current_date,
                    signed_minor_units=event.signed_minor_units,
                    metadata={"counterparty_name": event.counterparty_name, "risk_flags": event.risk_flags},
                )
            )

    weekly_buckets: List[WeeklyForecastBucket] = []
    for week_index, bucket_start, bucket_end in seven_day_windows(start_date, forecast_input.horizon_days):
        bucket_points = [point for point in daily_points if bucket_start <= point.date <= bucket_end]
        if not bucket_points:
            continue
        bucket_event_ids = []
        for point in bucket_points:
            bucket_event_ids.extend(point.event_ids)
        weekly_buckets.append(
            WeeklyForecastBucket(
                week_index=week_index,
                label="Week {index}".format(index=week_index),
                start_date=bucket_start,
                end_date=bucket_end,
                opening_balance_minor_units=bucket_points[0].opening_balance_minor_units,
                inflow_minor_units=sum(point.inflow_minor_units for point in bucket_points),
                outflow_minor_units=sum(point.outflow_minor_units for point in bucket_points),
                net_movement_minor_units=sum(point.net_movement_minor_units for point in bucket_points),
                closing_balance_minor_units=bucket_points[-1].closing_balance_minor_units,
                minimum_balance_minor_units=min(point.closing_balance_minor_units for point in bucket_points),
                event_ids=bucket_event_ids,
            )
        )

    run = ForecastRun(
        org_id=forecast_input.profile.org_id,
        profile=forecast_input.profile,
        as_of_date=forecast_input.as_of_date,
        horizon_days=forecast_input.horizon_days,
        calendar_version=CALENDAR_VERSION,
        rule_version=RULE_VERSION,
        formula_version=FORMULA_VERSION,
        scenario=active_scenario,
        opening_balance_minor_units=forecast_input.opening_balance.balance_minor_units,
        resolved_events=resolved_events,
        daily_points=daily_points,
        weekly_buckets=weekly_buckets,
        alerts=alerts,
        audit_trace=audit_trace,
    )
    run.kpis = build_kpis(run, forecast_input)
    return run


def build_standard_scenario_runs(forecast_input: ForecastInput) -> List[ForecastRun]:
    return [build_forecast_run(forecast_input, scenario=scenario) for scenario in standard_scenario_variants(forecast_input.scenario)]
