from collections import defaultdict
from typing import Dict, List, Optional

from cashflow_os.domain.models import (
    ChartSeries,
    ChartSpec,
    EntityType,
    ForecastRun,
    KPIValue,
    ReportPack,
    ReportSection,
)
from cashflow_os.reports.traces import (
    aging_bucket_label,
    build_cash_bridge_trace_points,
    build_compliance_trace_points,
    build_concentration_trace_points,
    build_weekly_trace_points,
    build_aging_trace_points,
    dump_trace_points,
)
from cashflow_os.reports.sparklines import build_kpi_sparklines
from cashflow_os.utils.money import format_inr


def _flatten_kpis(run: ForecastRun) -> Dict[str, KPIValue]:
    groups = [
        run.kpis.top_kpis,
        run.kpis.working_capital,
        run.kpis.manufacturer,
        run.kpis.compliance,
    ]
    flattened: Dict[str, KPIValue] = {}
    for group in groups:
        for item in group:
            flattened[item.key] = item
    return flattened


def _aging_buckets(run: ForecastRun, positive: bool) -> List[float]:
    bucket_map = defaultdict(int)
    for event in run.resolved_events:
        if positive and event.signed_minor_units <= 0:
            continue
        if not positive and event.signed_minor_units >= 0:
            continue
        bucket = aging_bucket_label(run, event)
        bucket_map[bucket] += abs(event.signed_minor_units)
    order = ["0-15", "16-30", "31-45", "46-60", "60+"]
    return [round(bucket_map[label] / 100.0, 2) for label in order]


def _concentration_top(run: ForecastRun, positive: bool) -> ChartSpec:
    totals = defaultdict(int)
    for event in run.resolved_events:
        if positive and event.signed_minor_units <= 0:
            continue
        if not positive and event.signed_minor_units >= 0:
            continue
        totals[event.counterparty_name or "Unassigned"] += abs(event.signed_minor_units)
    top_items = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
    return ChartSpec(
        kind="pareto",
        title="Customer Concentration" if positive else "Vendor Concentration",
        subtitle="Highlights concentration risk across the largest counterparties in the forecast horizon.",
        x_axis=[item[0] for item in top_items],
        series=[
            ChartSeries(
                name="Amount (₹)",
                kind="bar",
                values=[round(item[1] / 100.0, 2) for item in top_items],
            )
        ],
        meta={
            "trace_subject": "counterparty_concentration",
            "counterparty_names": [item[0] for item in top_items],
            "trace_points": dump_trace_points(build_concentration_trace_points(run, positive=positive)),
        },
    )


def _scenario_chart(run: ForecastRun, comparison_runs: Optional[List[ForecastRun]]) -> Optional[ChartSpec]:
    if not comparison_runs:
        return None
    labels = [comparison_run.scenario.name for comparison_run in comparison_runs]
    closing = [round(comparison_run.weekly_buckets[-1].closing_balance_minor_units / 100.0, 2) for comparison_run in comparison_runs]
    minimum = [round(min(bucket.minimum_balance_minor_units for bucket in comparison_run.weekly_buckets) / 100.0, 2) for comparison_run in comparison_runs]
    return ChartSpec(
        kind="scenario",
        title="Scenario Comparison",
        subtitle="Compares closing cash and minimum cash across base, stress, and upside assumptions.",
        x_axis=labels,
        series=[
            ChartSeries(name="Closing Cash", kind="bar", values=closing),
            ChartSeries(name="Minimum Cash", kind="line", values=minimum),
        ],
    )


def build_report_pack(run: ForecastRun, comparison_runs: Optional[List[ForecastRun]] = None) -> ReportPack:
    if not run.weekly_buckets:
        raise ValueError("Report pack requires at least one weekly bucket.")
    if run.kpis is None:
        raise ValueError("Report pack requires KPI data.")
    kpis = _flatten_kpis(run)
    weekly_labels = [bucket.label for bucket in run.weekly_buckets]
    charts = [
        ChartSpec(
            kind="line-area",
            title="13-Week Cash Balance",
            subtitle="Shows how projected closing cash moves across the forecast horizon.",
            x_axis=weekly_labels,
            series=[ChartSeries(name="Closing Cash", values=[round(bucket.closing_balance_minor_units / 100.0, 2) for bucket in run.weekly_buckets])],
            meta={
                "trace_subject": "weekly_cash_balance",
                "forecast_run_id": run.forecast_run_id,
                "trace_points": dump_trace_points(build_weekly_trace_points(run)),
            },
        ),
        ChartSpec(
            kind="stacked-bars",
            title="Weekly Cash In vs Cash Out",
            subtitle="Breaks each week into expected inflows and outflows to expose timing pressure.",
            x_axis=weekly_labels,
            series=[
                ChartSeries(name="Cash In", kind="bar", values=[round(bucket.inflow_minor_units / 100.0, 2) for bucket in run.weekly_buckets]),
                ChartSeries(name="Cash Out", kind="bar", values=[round(bucket.outflow_minor_units / 100.0, 2) for bucket in run.weekly_buckets]),
            ],
            meta={
                "trace_subject": "weekly_cash_movements",
                "forecast_run_id": run.forecast_run_id,
                "trace_points": dump_trace_points(build_weekly_trace_points(run)),
            },
        ),
        ChartSpec(
            kind="waterfall",
            title="Cash Bridge",
            subtitle="Explains how opening cash converts into ending cash across the full 13-week horizon.",
            x_axis=["Opening", "Net Movement", "Closing"],
            series=[
                ChartSeries(
                    name="Cash Bridge",
                    kind="bar",
                    values=[
                        round(run.opening_balance_minor_units / 100.0, 2),
                        round((run.weekly_buckets[-1].closing_balance_minor_units - run.opening_balance_minor_units) / 100.0, 2),
                        round(run.weekly_buckets[-1].closing_balance_minor_units / 100.0, 2),
                    ],
                )
            ],
            meta={
                "trace_subject": "cash_bridge",
                "forecast_run_id": run.forecast_run_id,
                "trace_points": dump_trace_points(build_cash_bridge_trace_points(run)),
            },
        ),
        ChartSpec(
            kind="heatmap",
            title="AR Aging Heatmap",
            subtitle="Buckets inflows by aging profile so delayed collections are visible quickly.",
            x_axis=["0-15", "16-30", "31-45", "46-60", "60+"],
            series=[ChartSeries(name="AR Aging", kind="heatmap", values=_aging_buckets(run, positive=True))],
            meta={
                "trace_subject": "receivables_aging",
                "forecast_run_id": run.forecast_run_id,
                "trace_points": dump_trace_points(build_aging_trace_points(run, positive=True)),
            },
        ),
        ChartSpec(
            kind="heatmap",
            title="AP Due Calendar",
            subtitle="Shows payable timing pressure across the next due buckets so vendor cash calls are not hidden.",
            x_axis=["0-15", "16-30", "31-45", "46-60", "60+"],
            series=[ChartSeries(name="AP Due", kind="heatmap", values=_aging_buckets(run, positive=False))],
            meta={
                "trace_subject": "payables_aging",
                "forecast_run_id": run.forecast_run_id,
                "trace_points": dump_trace_points(build_aging_trace_points(run, positive=False)),
            },
        ),
        ChartSpec(
            kind="timeline",
            title="Compliance Timeline",
            subtitle="Shows GST, TDS, EPF, payroll, and EMI obligations scheduled in the next 13 weeks.",
            x_axis=[event.scheduled_date.isoformat() for event in run.resolved_events if event.entity_type in (EntityType.GST, EntityType.TDS, EntityType.EPF, EntityType.PAYROLL, EntityType.EMI)],
            series=[ChartSeries(name="Compliance Outflow", kind="bar", values=[round(abs(event.signed_minor_units) / 100.0, 2) for event in run.resolved_events if event.entity_type in (EntityType.GST, EntityType.TDS, EntityType.EPF, EntityType.PAYROLL, EntityType.EMI)])],
            meta={
                "trace_subject": "compliance_timeline",
                "forecast_run_id": run.forecast_run_id,
                "trace_points": dump_trace_points(build_compliance_trace_points(run)),
            },
        ),
        _concentration_top(run, positive=True),
        _concentration_top(run, positive=False),
    ]

    scenario_chart = _scenario_chart(run, comparison_runs)
    if scenario_chart is not None:
        charts.append(scenario_chart)

    minimum_cash = kpis["minimum_cash"].value
    closing_cash = kpis["closing_cash"].value
    overdue_receivables = kpis["overdue_receivables"].value

    sections = [
        ReportSection(
            title="Executive Summary",
            narrative=(
                "The forecast closes at {closing} with a minimum balance of {minimum}. "
                "Overdue receivables total {overdue}, so collections timing remains the dominant operating risk."
            ).format(
                closing=format_inr(closing_cash),
                minimum=format_inr(minimum_cash),
                overdue=format_inr(overdue_receivables),
            ),
            chart_ids=[charts[0].chart_id, charts[1].chart_id, charts[2].chart_id],
            rows=[
                {"metric": item.label, "value": item.value, "unit": item.unit}
                for item in run.kpis.top_kpis[:8]
            ],
        ),
        ReportSection(
            title="Working Capital",
            narrative="Working-capital metrics combine overdue exposure, estimated collection/payment days, and inventory cover to highlight liquidity pressure drivers.",
            chart_ids=[charts[3].chart_id, charts[4].chart_id, charts[6].chart_id, charts[7].chart_id],
            rows=[{"metric": item.label, "value": item.value, "unit": item.unit} for item in run.kpis.working_capital],
        ),
        ReportSection(
            title="Compliance and Risk",
            narrative="This section surfaces upcoming statutory obligations and MSME payable pressure so finance teams can prioritize cash deployment without missing regulatory deadlines.",
            chart_ids=[charts[5].chart_id],
            rows=[
                {"title": alert.title, "severity": alert.severity.value, "message": alert.message, "due_date": alert.due_date}
                for alert in run.alerts[:8]
            ],
        ),
    ]

    if run.kpis.manufacturer:
        sections.append(
            ReportSection(
                title="Manufacturer Lens",
                narrative="Inventory cover and counterparty concentration metrics make the forecast more relevant for inventory-led and supplier-dependent businesses.",
                rows=[{"metric": item.label, "value": item.value, "unit": item.unit} for item in run.kpis.manufacturer],
            )
        )

    msme_vendors = []
    seen_vendors = set()
    for alert in run.alerts:
        if "MSME" in alert.title or "43B" in alert.title:
            vendor_name = alert.message.split(":")[-1].strip() if ":" in alert.message else "Unknown Vendor"
            if vendor_name in seen_vendors:
                continue
            seen_vendors.add(vendor_name)
            msme_vendors.append({
                "vendor": vendor_name,
                "amount": format_inr(alert.amount_minor_units) if alert.amount_minor_units else "N/A",
                "due_date": str(alert.due_date) if alert.due_date else "N/A",
                "severity": alert.severity.value,
                "risk_level": "High" if alert.severity.value == "critical" else "Medium" if alert.severity.value == "warning" else "Low",
            })
    if msme_vendors:
        sections.append(
            ReportSection(
                title="MSME Vendor Risk Table",
                narrative="Under Section 43B(h) of the Income Tax Act, payments to MSME vendors exceeding 45 days cannot be claimed as business expenses. This table highlights at-risk payables.",
                rows=msme_vendors,
            )
        )

    if scenario_chart is not None:
        sections.append(
            ReportSection(
                title="Scenario Comparison",
                narrative="Standard base, stress, and upside scenarios are generated from the same canonical cash-event set so users can compare outcomes without losing auditability.",
                chart_ids=[scenario_chart.chart_id],
            )
        )

    sparklines = build_kpi_sparklines(
        weekly_closing_minor_units=[b.closing_balance_minor_units for b in run.weekly_buckets],
        weekly_inflow_minor_units=[b.inflow_minor_units for b in run.weekly_buckets],
        weekly_outflow_minor_units=[b.outflow_minor_units for b in run.weekly_buckets],
    )

    return ReportPack(
        forecast_run_id=run.forecast_run_id,
        title="{company} Cashflow Pack".format(company=run.profile.company_name),
        charts=charts,
        sections=sections,
        methodology_notes=[
            "Direct cash forecast computed at daily granularity and presented in weekly buckets.",
            "Money stored and calculated in integer paise; display formatting only happens at export time.",
            "Compliance events for GST, TDS, EPF, payroll, EMI, and MSME risk are generated by the rule engine.",
            "Collections and payments use due dates first, then behavioral delays, then scenario adjustments.",
        ],
        sparklines=sparklines,
    )
