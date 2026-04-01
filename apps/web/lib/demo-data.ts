import type { AlertItem, Metric } from "@/components/cards";
import type { DashboardChart, DashboardChartTracePoint } from "@/lib/dashboard-types";
import { getApiBaseUrl, getApiRequestHeaders } from "@/lib/api";

type ApiChartSeries = {
  name: string;
  kind: string;
  values: number[];
};

type ApiChartSpec = {
  chart_id: string;
  kind: string;
  title: string;
  subtitle: string;
  x_axis: string[];
  series: ApiChartSeries[];
  meta: Record<string, unknown>;
};

type ApiReportPack = {
  report_id: string;
  charts: ApiChartSpec[];
};

type ApiMetric = {
  key: string;
  label: string;
  unit: string;
  value: number | string;
  description?: string;
};

type ApiAlert = {
  title: string;
  message: string;
  severity: "info" | "warning" | "critical";
  due_date?: string;
  amount_minor_units?: number | null;
};

type ApiDashboardResponse = {
  forecast_run: {
    forecast_run_id: string;
    profile: {
      company_name: string;
    };
    scenario: {
      name: string;
    };
    as_of_date: string;
    kpis: {
      top_kpis: ApiMetric[];
      working_capital: ApiMetric[];
      manufacturer: ApiMetric[];
      compliance: ApiMetric[];
    };
    alerts: ApiAlert[];
  };
  report_pack: ApiReportPack;
};

export type DashboardPayload = {
  reportId: string;
  forecastRunId: string;
  companyName: string;
  scenarioName: string;
  asOfDate: string;
  liveData: boolean;
  topKpis: Metric[];
  workingCapital: Metric[];
  manufacturer: Metric[];
  compliance: Metric[];
  alerts: AlertItem[];
  charts: DashboardChart[];
};

const demoTopKpis: Metric[] = [
  { key: "opening_cash", label: "Opening Cash", unit: "money", value: 1800000 },
  { key: "closing_cash", label: "Closing Cash", unit: "money", value: -383500 },
  { key: "minimum_cash", label: "Minimum Cash", unit: "money", value: -383500 },
  { key: "net_cash_flow", label: "Net Cash Flow", unit: "money", value: -2183500 },
  { key: "cash_in", label: "Cash In", unit: "money", value: 2041500 },
  { key: "cash_out", label: "Cash Out", unit: "money", value: 4225000 },
  { key: "weeks_to_shortfall", label: "Weeks to Shortfall", unit: "weeks", value: 8 },
  { key: "buffer_coverage", label: "Buffer Coverage", unit: "percent", value: 80.2 }
];

const demoWorkingCapital: Metric[] = [
  { key: "overdue_receivables", label: "Overdue Receivables", unit: "money", value: 841500 },
  { key: "overdue_payables", label: "Overdue Payables", unit: "money", value: 900000 },
  { key: "dso", label: "DSO", unit: "days", value: 12.4 },
  { key: "dpo", label: "DPO", unit: "days", value: 15.8 },
  { key: "dio", label: "DIO", unit: "days", value: 23.0 },
  { key: "ccc", label: "Cash Conversion Cycle", unit: "days", value: 19.6 },
  { key: "collection_reliability", label: "Collection Reliability", unit: "score", value: 63.5 }
];

const demoManufacturer: Metric[] = [
  { key: "inventory_cover", label: "Inventory Cover", unit: "days", value: 23 },
  { key: "customer_concentration", label: "Customer Concentration", unit: "percent", value: 58.5 },
  { key: "vendor_concentration", label: "Vendor Concentration", unit: "percent", value: 65.4 }
];

const demoCompliance: Metric[] = [
  { key: "msme_payable_risk", label: "MSME Payable at Risk", unit: "money", value: 900000 },
  { key: "gst_next_30", label: "GST Due Next 30 Days", unit: "money", value: 220000 },
  { key: "tds_next_30", label: "TDS Due Next 30 Days", unit: "money", value: 65000 },
  { key: "epf_payroll_next_30", label: "EPF & Payroll Due Next 30 Days", unit: "money", value: 400000 }
];

const demoAlerts: AlertItem[] = [
  {
    title: "MSME vendor payment exceeds statutory threshold",
    message: "Apex Steel is marked as MSME and the payable is projected beyond the 45-day statutory threshold.",
    severity: "critical",
    dueDate: "2026-04-15",
    amount: 900000
  },
  {
    title: "Cash buffer breached",
    message: "Projected balance drops below the configured cash buffer as collection timing slips and statutory dues stack up.",
    severity: "warning",
    dueDate: "2026-05-20",
    amount: 118500
  },
  {
    title: "Projected cash shortfall",
    message: "The business turns negative in week 8 without corrective action on collections, financing, or payment timing.",
    severity: "critical",
    dueDate: "2026-05-27",
    amount: 18500
  }
];

function demoTracePoints(labels: string[], summaries?: string[]): DashboardChartTracePoint[] {
  return labels.map((label, index) => ({
    key: label.toLowerCase().replace(/\s+/g, "-"),
    label,
    summary: summaries?.[index]
  }));
}

const demoCharts: DashboardChart[] = [
  {
    chartId: "demo-line-area",
    kind: "line-area",
    title: "13-Week Cash Balance",
    subtitle: "Shows how projected closing cash moves across the forecast horizon.",
    xAxis: Array.from({ length: 13 }, (_, index) => `Week ${index + 1}`),
    series: [
      {
        name: "Closing Cash",
        kind: "line",
        values: [1085000, 1700000, 800000, 1421500, 881500, 481500, 341500, -18500, -238500, -343500, -383500, -383500, -383500]
      }
    ],
    traceSubject: "weekly_cash_balance",
    tracePoints: demoTracePoints(Array.from({ length: 13 }, (_, index) => `Week ${index + 1}`))
  },
  {
    chartId: "demo-stacked-bars",
    kind: "stacked-bars",
    title: "Weekly Cash In vs Cash Out",
    subtitle: "Breaks each week into expected inflows and outflows to expose timing pressure.",
    xAxis: Array.from({ length: 13 }, (_, index) => `Week ${index + 1}`),
    series: [
      { name: "Cash In", kind: "bar", values: [0, 1200000, 0, 841500, 0, 0, 0, 0, 0, 0, 0, 0, 0] },
      { name: "Cash Out", kind: "bar", values: [715000, 585000, 900000, 220000, 540000, 400000, 140000, 360000, 220000, 105000, 40000, 0, 0] }
    ],
    traceSubject: "weekly_cash_movements",
    tracePoints: demoTracePoints(Array.from({ length: 13 }, (_, index) => `Week ${index + 1}`))
  },
  {
    chartId: "demo-waterfall",
    kind: "waterfall",
    title: "Cash Bridge",
    subtitle: "Explains how opening cash converts into ending cash across the full 13-week horizon.",
    xAxis: ["Opening", "Net Movement", "Closing"],
    series: [{ name: "Cash Bridge", kind: "bar", values: [1800000, -2183500, -383500] }],
    traceSubject: "cash_bridge",
    tracePoints: demoTracePoints(["Opening", "Net Movement", "Closing"])
  },
  {
    chartId: "demo-ar-aging",
    kind: "heatmap",
    title: "AR Aging Heatmap",
    subtitle: "Buckets inflows by aging profile so delayed collections are visible quickly.",
    xAxis: ["0-15", "16-30", "31-45", "46-60", "60+"],
    series: [{ name: "AR Aging", kind: "heatmap", values: [325000, 516500, 0, 0, 0] }],
    traceSubject: "receivables_aging",
    tracePoints: demoTracePoints(["0-15", "16-30", "31-45", "46-60", "60+"])
  },
  {
    chartId: "demo-ap-aging",
    kind: "heatmap",
    title: "AP Due Calendar",
    subtitle: "Shows payable timing pressure across the next due buckets so vendor cash calls are not hidden.",
    xAxis: ["0-15", "16-30", "31-45", "46-60", "60+"],
    series: [{ name: "AP Due", kind: "heatmap", values: [475000, 900000, 0, 0, 0] }],
    traceSubject: "payables_aging",
    tracePoints: demoTracePoints(["0-15", "16-30", "31-45", "46-60", "60+"])
  },
  {
    chartId: "demo-compliance",
    kind: "timeline",
    title: "Compliance Timeline",
    subtitle: "Shows GST, TDS, EPF, payroll, and EMI obligations scheduled in the next 13 weeks.",
    xAxis: ["2026-04-05", "2026-04-07", "2026-04-15", "2026-04-20", "2026-05-01"],
    series: [{ name: "Compliance Outflow", kind: "bar", values: [110000, 65000, 40000, 220000, 360000] }],
    traceSubject: "compliance_timeline",
    tracePoints: demoTracePoints([
      "EMI on 2026-04-05",
      "TDS on 2026-04-07",
      "EPF on 2026-04-15",
      "GST on 2026-04-20",
      "PAYROLL on 2026-05-01"
    ])
  },
  {
    chartId: "demo-customer-pareto",
    kind: "pareto",
    title: "Customer Concentration",
    subtitle: "Highlights concentration risk across the largest counterparties in the forecast horizon.",
    xAxis: ["Sharma Retail", "Delta Foods", "Unassigned"],
    series: [{ name: "Amount (₹)", kind: "bar", values: [1200000, 841500, 0] }],
    traceSubject: "counterparty_concentration",
    tracePoints: demoTracePoints(["Sharma Retail", "Delta Foods", "Unassigned"])
  },
  {
    chartId: "demo-vendor-pareto",
    kind: "pareto",
    title: "Vendor Concentration",
    subtitle: "Highlights concentration risk across the largest counterparties in the forecast horizon.",
    xAxis: ["Apex Steel", "Universal Packaging", "Utilities"],
    series: [{ name: "Amount (₹)", kind: "bar", values: [900000, 475000, 85000] }],
    traceSubject: "counterparty_concentration",
    tracePoints: demoTracePoints(["Apex Steel", "Universal Packaging", "Utilities"])
  },
  {
    chartId: "demo-scenario",
    kind: "scenario",
    title: "Scenario Comparison",
    subtitle: "Compares closing cash and minimum cash across base, stress, and upside assumptions.",
    xAxis: ["Base Case", "Stress Case", "Upside Case"],
    series: [
      { name: "Closing Cash", kind: "bar", values: [-383500, -861000, 405000] },
      { name: "Minimum Cash", kind: "line", values: [-383500, -1032000, 180000] }
    ],
    tracePoints: []
  }
];

const demoPayload: DashboardPayload = {
  reportId: "demo-report",
  forecastRunId: "demo",
  companyName: "Shakti Components Pvt Ltd",
  scenarioName: "Base Case",
  asOfDate: "2026-04-01",
  liveData: false,
  topKpis: demoTopKpis,
  workingCapital: demoWorkingCapital,
  manufacturer: demoManufacturer,
  compliance: demoCompliance,
  alerts: demoAlerts,
  charts: demoCharts
};

function mapMetrics(items: ApiMetric[]): Metric[] {
  return items.map((item) => ({
    ...item,
    value: item.unit === "money" ? Number(item.value) / 100 : item.value
  }));
}

function mapAlerts(items: ApiAlert[]): AlertItem[] {
  return items.map((alert) => ({
    title: alert.title,
    message: alert.message,
    severity: alert.severity,
    dueDate: alert.due_date,
    amount:
      alert.amount_minor_units === null || alert.amount_minor_units === undefined
        ? undefined
        : alert.amount_minor_units / 100
  }));
}

function mapTracePoints(value: unknown): DashboardChartTracePoint[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.flatMap((entry, index) => {
    if (!entry || typeof entry !== "object") {
      return [];
    }
    const point = entry as Record<string, unknown>;
    const key = typeof point.key === "string" ? point.key : `point-${index}`;
    const label = typeof point.label === "string" ? point.label : key;
    return [
      {
        key,
        label,
        summary: typeof point.summary === "string" ? point.summary : undefined
      }
    ];
  });
}

function buildDashboardCharts(reportPack: ApiReportPack): DashboardChart[] {
  return reportPack.charts.map((chart) => {
    const traceSubject =
      typeof chart.meta.trace_subject === "string" ? chart.meta.trace_subject : undefined;

    return {
      chartId: chart.chart_id,
      kind: chart.kind,
      title: chart.title,
      subtitle: chart.subtitle,
      xAxis: chart.x_axis,
      series: chart.series.map((series) => ({
        name: series.name,
        kind: series.kind,
        values: series.values
      })),
      traceSubject,
      tracePoints: mapTracePoints(chart.meta.trace_points)
    };
  });
}

export async function getDashboardData(forecastRunId?: string, apiToken?: string | null): Promise<DashboardPayload> {
  const apiBase = getApiBaseUrl();
  if (!apiBase) {
    return demoPayload;
  }

  try {
    const query = forecastRunId
      ? `forecast_run_id=${encodeURIComponent(forecastRunId)}`
      : "demo=1";
    const response = await fetch(`${apiBase}/v1/dashboards/cash?${query}`, {
      cache: "no-store",
      headers: getApiRequestHeaders(undefined, apiToken)
    });
    if (!response.ok) {
      return demoPayload;
    }

    const payload = (await response.json()) as ApiDashboardResponse;
    const forecastRun = payload.forecast_run;
    return {
      reportId: payload.report_pack.report_id,
      forecastRunId: forecastRun.forecast_run_id,
      companyName: forecastRun.profile.company_name,
      scenarioName: forecastRun.scenario.name,
      asOfDate: forecastRun.as_of_date,
      liveData: true,
      topKpis: mapMetrics(forecastRun.kpis.top_kpis),
      workingCapital: mapMetrics(forecastRun.kpis.working_capital),
      manufacturer: mapMetrics(forecastRun.kpis.manufacturer),
      compliance: mapMetrics(forecastRun.kpis.compliance),
      alerts: mapAlerts(forecastRun.alerts),
      charts: buildDashboardCharts(payload.report_pack)
    };
  } catch {
    return demoPayload;
  }
}
