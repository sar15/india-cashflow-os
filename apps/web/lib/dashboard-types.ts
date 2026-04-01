export type DashboardChartTracePoint = {
  key: string;
  label: string;
  summary?: string;
};

export type DashboardChartSeries = {
  name: string;
  kind: string;
  values: number[];
};

export type DashboardChart = {
  chartId: string;
  kind: string;
  title: string;
  subtitle: string;
  xAxis: string[];
  series: DashboardChartSeries[];
  traceSubject?: string;
  tracePoints: DashboardChartTracePoint[];
};

export type DashboardTraceTotals = {
  event_count: number;
  trace_count: number;
  inflow_minor_units: number;
  outflow_minor_units: number;
  net_minor_units: number;
};

export type DashboardTraceEvent = {
  event_id: string;
  display_name: string;
  entity_type: string;
  counterparty_name?: string | null;
  scheduled_date: string;
  signed_minor_units: number;
  source_confidence: number;
  mapping_confidence: number;
  is_generated: boolean;
  risk_flags: string[];
  reason: string;
};

export type DashboardAuditTrace = {
  trace_id: string;
  event_id: string;
  subject: string;
  explanation: string;
  effective_date?: string | null;
  bucket_label?: string | null;
  signed_minor_units?: number | null;
  metadata: Record<string, unknown>;
};

export type DashboardTrace = {
  report_id: string;
  chart_id: string;
  chart_title: string;
  chart_kind: string;
  trace_subject: string;
  point_key?: string | null;
  point_label?: string | null;
  summary: string;
  totals: DashboardTraceTotals;
  events: DashboardTraceEvent[];
  traces: DashboardAuditTrace[];
};
