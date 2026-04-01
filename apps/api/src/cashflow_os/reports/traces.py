from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from cashflow_os.domain.models import (
    ChartSpec,
    ChartTracePoint,
    ChartTraceResponse,
    ChartTraceTotals,
    EntityType,
    ForecastRun,
    ResolvedCashEvent,
    ReportPack,
)
from cashflow_os.utils.money import format_inr


AGING_BUCKET_ORDER = ["0-15", "16-30", "31-45", "46-60", "60+"]
COMPLIANCE_ENTITY_TYPES = {
    EntityType.GST,
    EntityType.TDS,
    EntityType.EPF,
    EntityType.PAYROLL,
    EntityType.EMI,
}


def aging_bucket_label(run: ForecastRun, event: ResolvedCashEvent) -> str:
    age_days = abs((event.scheduled_date - run.as_of_date).days)
    if age_days <= 15:
        return "0-15"
    if age_days <= 30:
        return "16-30"
    if age_days <= 45:
        return "31-45"
    if age_days <= 60:
        return "46-60"
    return "60+"


def build_weekly_trace_points(run: ForecastRun) -> List[ChartTracePoint]:
    points: List[ChartTracePoint] = []
    for bucket in run.weekly_buckets:
        points.append(
            ChartTracePoint(
                key=bucket.label,
                label=bucket.label,
                event_ids=bucket.event_ids,
                summary=(
                    "{label} closes at {closing} after inflows of {inflow} and outflows of {outflow}."
                ).format(
                    label=bucket.label,
                    closing=format_inr(bucket.closing_balance_minor_units),
                    inflow=format_inr(bucket.inflow_minor_units),
                    outflow=format_inr(bucket.outflow_minor_units),
                ),
            )
        )
    return points


def build_cash_bridge_trace_points(run: ForecastRun) -> List[ChartTracePoint]:
    all_event_ids = [event.event_id for event in run.resolved_events]
    return [
        ChartTracePoint(
            key="opening",
            label="Opening",
            summary="Opening cash is the starting bank position on the forecast as-of date.",
        ),
        ChartTracePoint(
            key="net_movement",
            label="Net Movement",
            event_ids=all_event_ids,
            summary="Net movement combines every included inflow and outflow scheduled across the 13-week horizon.",
        ),
        ChartTracePoint(
            key="closing",
            label="Closing",
            event_ids=all_event_ids,
            summary="Closing cash reflects the opening balance plus all scheduled net cash movement in the forecast horizon.",
        ),
    ]


def build_aging_trace_points(run: ForecastRun, *, positive: bool) -> List[ChartTracePoint]:
    bucket_event_ids: Dict[str, List[str]] = defaultdict(list)
    bucket_totals: Dict[str, int] = defaultdict(int)
    for event in run.resolved_events:
        if positive and event.signed_minor_units <= 0:
            continue
        if not positive and event.signed_minor_units >= 0:
            continue
        bucket = aging_bucket_label(run, event)
        bucket_event_ids[bucket].append(event.event_id)
        bucket_totals[bucket] += abs(event.signed_minor_units)

    label_prefix = "receivable" if positive else "payable"
    return [
        ChartTracePoint(
            key=bucket,
            label=bucket,
            event_ids=bucket_event_ids.get(bucket, []),
            summary=(
                "{bucket} contains {count} {label_prefix} items totalling {total}."
            ).format(
                bucket=bucket,
                count=len(bucket_event_ids.get(bucket, [])),
                label_prefix=label_prefix,
                total=format_inr(bucket_totals.get(bucket, 0)),
            ),
        )
        for bucket in AGING_BUCKET_ORDER
    ]


def build_compliance_trace_points(run: ForecastRun) -> List[ChartTracePoint]:
    points: List[ChartTracePoint] = []
    for event in run.resolved_events:
        if event.entity_type not in COMPLIANCE_ENTITY_TYPES:
            continue
        label = "{entity} on {date}".format(
            entity=event.entity_type.value.upper(),
            date=event.scheduled_date.isoformat(),
        )
        points.append(
            ChartTracePoint(
                key=event.event_id,
                label=label,
                event_ids=[event.event_id],
                summary="{label} is scheduled for {amount}.".format(
                    label=label,
                    amount=format_inr(abs(event.signed_minor_units)),
                ),
            )
        )
    return points


def build_concentration_trace_points(run: ForecastRun, *, positive: bool) -> List[ChartTracePoint]:
    totals: Dict[str, int] = defaultdict(int)
    event_ids_by_name: Dict[str, List[str]] = defaultdict(list)
    for event in run.resolved_events:
        if positive and event.signed_minor_units <= 0:
            continue
        if not positive and event.signed_minor_units >= 0:
            continue
        name = event.counterparty_name or "Unassigned"
        totals[name] += abs(event.signed_minor_units)
        event_ids_by_name[name].append(event.event_id)

    label_prefix = "inflow" if positive else "outflow"
    top_items = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
    return [
        ChartTracePoint(
            key=name,
            label=name,
            event_ids=event_ids_by_name[name],
            summary="{name} contributes {amount} of projected {label_prefix} exposure.".format(
                name=name,
                amount=format_inr(amount),
                label_prefix=label_prefix,
            ),
        )
        for name, amount in top_items
    ]


def dump_trace_points(points: Iterable[ChartTracePoint]) -> List[dict]:
    return [point.model_dump(mode="json") for point in points]


def _get_chart(report_pack: ReportPack, chart_id: str) -> ChartSpec:
    for chart in report_pack.charts:
        if chart.chart_id == chart_id:
            return chart
    raise LookupError("Chart not found")


def _load_trace_points(chart: ChartSpec) -> List[ChartTracePoint]:
    raw_points = chart.meta.get("trace_points", [])
    return [ChartTracePoint.model_validate(point) for point in raw_points]


def _events_for_ids(run: ForecastRun, event_ids: Iterable[str]) -> List[ResolvedCashEvent]:
    events_by_id = {event.event_id: event for event in run.resolved_events}
    events = [events_by_id[event_id] for event_id in dict.fromkeys(event_ids) if event_id in events_by_id]
    return sorted(events, key=lambda event: (event.scheduled_date, -abs(event.signed_minor_units), event.display_name))


def resolve_report_chart_trace(
    report_pack: ReportPack,
    run: ForecastRun,
    chart_id: str,
    *,
    point_key: Optional[str] = None,
) -> ChartTraceResponse:
    chart = _get_chart(report_pack, chart_id)
    trace_points = _load_trace_points(chart)
    selected_point = None
    if point_key is not None:
        selected_point = next((point for point in trace_points if point.key == point_key), None)
        if selected_point is None:
            raise ValueError("Trace point not found")

    if selected_point is not None:
        event_ids = selected_point.event_ids
        summary = selected_point.summary or chart.subtitle
        point_label = selected_point.label
    else:
        event_ids = [event_id for point in trace_points for event_id in point.event_ids]
        summary = chart.subtitle
        point_label = None

    events = _events_for_ids(run, event_ids)
    event_ids_set = {event.event_id for event in events}
    traces = [trace for trace in run.audit_trace if trace.event_id in event_ids_set]
    inflow_minor_units = sum(event.signed_minor_units for event in events if event.signed_minor_units > 0)
    outflow_minor_units = sum(abs(event.signed_minor_units) for event in events if event.signed_minor_units < 0)
    totals = ChartTraceTotals(
        event_count=len(events),
        trace_count=len(traces),
        inflow_minor_units=inflow_minor_units,
        outflow_minor_units=outflow_minor_units,
        net_minor_units=inflow_minor_units - outflow_minor_units,
    )

    return ChartTraceResponse(
        report_id=report_pack.report_id,
        chart_id=chart.chart_id,
        chart_title=chart.title,
        chart_kind=chart.kind,
        trace_subject=str(chart.meta.get("trace_subject", "chart")),
        point_key=selected_point.key if selected_point is not None else None,
        point_label=point_label,
        summary=summary,
        totals=totals,
        events=events,
        traces=traces,
    )
