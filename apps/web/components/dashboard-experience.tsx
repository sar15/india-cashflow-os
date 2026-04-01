"use client";

import { startTransition, useState } from "react";

import { AlertList, KpiCard, MetricTable, SectionCard } from "@/components/cards";
import { ForecastChart } from "@/components/charts";
import type { DashboardPayload } from "@/lib/demo-data";
import type {
  DashboardChart,
  DashboardChartTracePoint,
  DashboardTrace
} from "@/lib/dashboard-types";
import { formatCurrency } from "@/lib/formatters";

function findChart(charts: DashboardChart[], title: string) {
  return charts.find((chart) => chart.title === title);
}

function renderTracePanel(
  dashboard: DashboardPayload,
  trace: DashboardTrace | null,
  isLoading: boolean,
  error: string | null
) {
  if (error) {
    return <div className="status-copy error">{error}</div>;
  }

  if (isLoading) {
    return <div className="status-copy">Loading event trace and audit notes for the selected chart point.</div>;
  }

  if (!dashboard.liveData) {
    return (
      <div className="status-copy">
        Chart drill-down is wired in, but demo mode does not carry live event-level trace data. Point the dashboard at the API to inspect source events.
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="status-copy">
        Click a chart point or bar to inspect the underlying events, applied rules, and audit reasoning for that number.
      </div>
    );
  }

  return (
    <div className="trace-panel">
      <div className="trace-summary">
        <div>
          <div className="pill">Trace focus</div>
          <h4 className="trace-title">{trace.point_label ?? trace.chart_title}</h4>
        </div>
        <p>{trace.summary}</p>
      </div>

      <div className="trace-stats">
        <div className="metric-chip">
          <span className="kpi-label">Net</span>
          <strong>{formatCurrency(trace.totals.net_minor_units / 100)}</strong>
        </div>
        <div className="metric-chip">
          <span className="kpi-label">Inflows</span>
          <strong>{formatCurrency(trace.totals.inflow_minor_units / 100)}</strong>
        </div>
        <div className="metric-chip">
          <span className="kpi-label">Outflows</span>
          <strong>{formatCurrency(trace.totals.outflow_minor_units / 100)}</strong>
        </div>
        <div className="metric-chip">
          <span className="kpi-label">Events</span>
          <strong>{trace.totals.event_count}</strong>
        </div>
      </div>

      {trace.events.length > 0 ? (
        <div className="trace-list">
          {trace.events.map((event) => (
            <article key={event.event_id} className="trace-event-card">
              <div className="trace-event-head">
                <div>
                  <strong>{event.display_name}</strong>
                  <div className="kpi-description">
                    {event.counterparty_name ? `${event.counterparty_name} · ` : ""}
                    {event.entity_type.toUpperCase()} · {event.scheduled_date}
                  </div>
                </div>
                <strong>{formatCurrency(event.signed_minor_units / 100)}</strong>
              </div>
              <p className="kpi-description">{event.reason}</p>
              <div className="trace-meta-row">
                <span>Source confidence {Math.round(event.source_confidence * 100)}%</span>
                <span>Mapping confidence {Math.round(event.mapping_confidence * 100)}%</span>
                <span>{event.is_generated ? "System generated" : "Imported"}</span>
              </div>
              {event.risk_flags.length > 0 ? (
                <div className="tag-list">
                  {event.risk_flags.map((riskFlag) => (
                    <span key={riskFlag} className="tag">
                      {riskFlag}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="status-copy">No event-level entries were attached to this chart point.</div>
      )}

      {trace.traces.length > 0 ? (
        <div className="trace-audit-list">
          <h4 className="trace-subtitle">Audit notes</h4>
          {trace.traces.slice(0, 5).map((traceEntry) => (
            <div key={traceEntry.trace_id} className="trace-note">
              <strong>{traceEntry.effective_date ?? "Run-level note"}</strong>
              <div className="kpi-description">{traceEntry.explanation}</div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function renderPreviewCard(dashboard: DashboardPayload) {
  return (
    <section className="report-card">
      <div className="report-preview">
        <div className="report-page">
          <h2 className="report-heading">Management Report Preview</h2>
          <div className="metric-strip">
            {dashboard.compliance.map((metric) => (
              <div key={metric.key} className="metric-chip">
                <span className="kpi-label">{metric.label}</span>
                <strong>
                  {metric.unit === "money"
                    ? formatCurrency(Number(metric.value))
                    : String(metric.value)}
                </strong>
              </div>
            ))}
          </div>
          <p className="kpi-description">
            PDF, Excel, and web views now share the same chart pack structure, scenario framing, and drill-down-ready trace metadata.
          </p>
        </div>
      </div>
    </section>
  );
}

export function DashboardExperience({ dashboard }: Readonly<{ dashboard: DashboardPayload }>) {
  const [selectedTrace, setSelectedTrace] = useState<DashboardTrace | null>(null);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const cashBalanceChart = findChart(dashboard.charts, "13-Week Cash Balance");
  const movementChart = findChart(dashboard.charts, "Weekly Cash In vs Cash Out");
  const bridgeChart = findChart(dashboard.charts, "Cash Bridge");
  const receivablesChart = findChart(dashboard.charts, "AR Aging Heatmap");
  const payablesChart = findChart(dashboard.charts, "AP Due Calendar");
  const complianceChart = findChart(dashboard.charts, "Compliance Timeline");
  const customerChart = findChart(dashboard.charts, "Customer Concentration");
  const vendorChart = findChart(dashboard.charts, "Vendor Concentration");
  const scenarioChart = findChart(dashboard.charts, "Scenario Comparison");

  async function handleTraceSelect(chart: DashboardChart, point: DashboardChartTracePoint) {
    if (!dashboard.liveData) {
      setSelectedTrace(null);
      setTraceError(null);
      return;
    }

    const activeKey = `${chart.chartId}:${point.key}`;
    setLoadingKey(activeKey);
    setTraceError(null);

    try {
      const response = await fetch(
        `/api/audit/trace?reportId=${encodeURIComponent(dashboard.reportId)}&chartId=${encodeURIComponent(chart.chartId)}&pointKey=${encodeURIComponent(point.key)}`,
        { cache: "no-store" }
      );
      const payload = (await response.json()) as DashboardTrace | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload && typeof payload.error === "string" ? payload.error : "Unable to load chart trace.");
      }
      startTransition(() => {
        setSelectedTrace(payload as DashboardTrace);
      });
    } catch (error) {
      setSelectedTrace(null);
      setTraceError(error instanceof Error ? error.message : "Unable to load chart trace.");
    } finally {
      setLoadingKey(null);
    }
  }

  const pdfHref = `/api/reports/pdf?forecastRunId=${encodeURIComponent(dashboard.forecastRunId)}`;
  const xlsxHref = `/api/reports/xlsx?forecastRunId=${encodeURIComponent(dashboard.forecastRunId)}`;

  return (
    <>
      <section className="hero-card">
        <span className="eyebrow">
          {dashboard.scenarioName} · As of {dashboard.asOfDate}
          {dashboard.liveData ? " · Live trace-ready" : " · Demo mode"}
        </span>
        <div className="hero-grid">
          <div>
            <h1 className="page-title">{dashboard.companyName}</h1>
            <p>
              The dashboard combines direct cash visibility, compliance timing, working-capital KPIs, and drill-down audit trails so the
              finance team can move from a board view to source-event proof without leaving the cockpit.
            </p>
            <div className="page-actions">
              {dashboard.liveData ? (
                <>
                  <a className="button" href={pdfHref}>
                    Generate PDF pack
                  </a>
                  <a className="button secondary" href={xlsxHref}>
                    Generate Excel pack
                  </a>
                </>
              ) : (
                <>
                  <span className="button" aria-disabled="true">
                    PDF pack needs API
                  </span>
                  <span className="button secondary" aria-disabled="true">
                    Excel pack needs API
                  </span>
                </>
              )}
            </div>
          </div>
          <div className="report-card">
            <div className="metric-strip">
              {dashboard.topKpis.slice(0, 4).map((metric) => (
                <div key={metric.key} className="metric-chip">
                  <span className="kpi-label">{metric.label}</span>
                  <strong>
                    {metric.unit === "money" ? formatCurrency(Number(metric.value)) : String(metric.value)}
                  </strong>
                </div>
              ))}
            </div>
            <p className="kpi-description">
              Every chart point can now carry a trace key back to its underlying event set, turning auditability from a promise into a workflow.
            </p>
          </div>
        </div>
      </section>

      <section className="kpi-grid">
        {dashboard.topKpis.map((metric) => (
          <KpiCard key={metric.key} metric={metric} />
        ))}
      </section>

      <section className="dashboard-grid">
        <SectionCard
          title="13-Week Cash Balance"
          subtitle="The line turns from comfort to stress once collections slip and statutory outflows stack on top of routine operations."
          pill="Primary chart"
        >
          {cashBalanceChart ? (
            <ForecastChart
              chart={cashBalanceChart}
              onPointClick={(point) => handleTraceSelect(cashBalanceChart, point)}
            />
          ) : null}
        </SectionCard>

        <SectionCard
          title="Key Alerts"
          subtitle="Risk colors are reserved for true exceptions so the finance team can focus attention fast."
          pill="Action required"
        >
          <AlertList alerts={dashboard.alerts} />
        </SectionCard>
      </section>

      <section className="dashboard-grid">
        <SectionCard
          title="Cash In vs Cash Out"
          subtitle="Weekly inflow and outflow pairing makes timing pressure more obvious than a single closing-balance line."
          pill="Drill-down"
        >
          {movementChart ? (
            <ForecastChart chart={movementChart} onPointClick={(point) => handleTraceSelect(movementChart, point)} />
          ) : null}
        </SectionCard>

        <SectionCard
          title="Cash Bridge"
          subtitle="A management-friendly bridge from opening balance to ending balance using the same run as the charts and exports."
          pill="Drill-down"
        >
          {bridgeChart ? (
            <ForecastChart chart={bridgeChart} onPointClick={(point) => handleTraceSelect(bridgeChart, point)} />
          ) : null}
        </SectionCard>
      </section>

      <section className="three-column">
        <SectionCard
          title="Working Capital KPIs"
          subtitle="Derived from the active forecast, overdue exposure, and the inventory profile."
          pill="Finance"
        >
          <MetricTable metrics={dashboard.workingCapital} />
        </SectionCard>

        <SectionCard
          title="AR Aging"
          subtitle="Aging distribution helps collections follow-up stay targeted and visible."
          pill="Collections"
        >
          {receivablesChart ? (
            <ForecastChart chart={receivablesChart} onPointClick={(point) => handleTraceSelect(receivablesChart, point)} />
          ) : null}
        </SectionCard>

        <SectionCard
          title="AP Due Calendar"
          subtitle="Payables are rendered with the same traceable structure as receivables so vendor pressure stays visible."
          pill="Suppliers"
        >
          {payablesChart ? (
            <ForecastChart chart={payablesChart} onPointClick={(point) => handleTraceSelect(payablesChart, point)} />
          ) : null}
        </SectionCard>
      </section>

      <section className="dashboard-grid">
        <SectionCard
          title="Compliance Timeline"
          subtitle="Upcoming statutory and scheduled cash drains are surfaced in the same operating view as commercial events."
          pill="India rules"
        >
          {complianceChart ? (
            <ForecastChart chart={complianceChart} onPointClick={(point) => handleTraceSelect(complianceChart, point)} />
          ) : null}
        </SectionCard>

        <SectionCard
          title="Audit Drill-Down"
          subtitle="This panel turns chart clicks into source-event evidence, rule context, and audit notes."
          pill={selectedTrace ? "Loaded" : "Click a chart"}
        >
          {renderTracePanel(dashboard, selectedTrace, loadingKey !== null, traceError)}
        </SectionCard>
      </section>

      <section className="two-column">
        <SectionCard
          title="Customer Concentration"
          subtitle="Largest counterparties are shown as a proper Pareto so concentration risk is visible before collections slip."
          pill="Drill-down"
        >
          {customerChart ? (
            <ForecastChart chart={customerChart} onPointClick={(point) => handleTraceSelect(customerChart, point)} />
          ) : null}
        </SectionCard>

        <SectionCard
          title="Vendor Concentration"
          subtitle="Critical supplier exposure gets the same interactive treatment as customer concentration."
          pill="Drill-down"
        >
          {vendorChart ? (
            <ForecastChart chart={vendorChart} onPointClick={(point) => handleTraceSelect(vendorChart, point)} />
          ) : null}
        </SectionCard>
      </section>

      <section className="two-column">
        <SectionCard
          title="Manufacturer Lens"
          subtitle="Inventory cover and concentration metrics make the cockpit more useful for working-capital-intensive businesses."
        >
          <MetricTable metrics={dashboard.manufacturer} />
        </SectionCard>

        {scenarioChart ? (
          <SectionCard
            title="Scenario Comparison"
            subtitle="Base, stress, and upside views are generated from the same canonical event set so trade-offs stay comparable."
            pill="Phase 2"
          >
            <ForecastChart chart={scenarioChart} />
          </SectionCard>
        ) : (
          renderPreviewCard(dashboard)
        )}
      </section>
    </>
  );
}
