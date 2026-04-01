import { formatCurrency, formatValue } from "@/lib/formatters";

export type Metric = {
  key: string;
  label: string;
  unit: string;
  value: number | string;
  description?: string;
};

export type AlertItem = {
  title: string;
  message: string;
  severity: "info" | "warning" | "critical";
  dueDate?: string;
  amount?: number;
};

export function KpiCard({ metric }: Readonly<{ metric: Metric }>) {
  const display = metric.unit === "money" ? formatCurrency(Number(metric.value)) : formatValue(metric.value, metric.unit);
  return (
    <article className="kpi-card">
      <div className="kpi-label">{metric.label}</div>
      <div className="kpi-value">{display}</div>
      <div className="kpi-description">{metric.description ?? "Derived from the active forecast run and rule version."}</div>
    </article>
  );
}

export function SectionCard({
  title,
  subtitle,
  children,
  pill
}: Readonly<{ title: string; subtitle: string; pill?: string; children: React.ReactNode }>) {
  return (
    <section className="section-card">
      <div className="card-header">
        <div>
          <h3 className="card-title">{title}</h3>
          <p className="card-subtitle">{subtitle}</p>
        </div>
        {pill ? <span className="pill">{pill}</span> : null}
      </div>
      {children}
    </section>
  );
}

export function AlertList({ alerts }: Readonly<{ alerts: AlertItem[] }>) {
  return (
    <div className="alert-list">
      {alerts.map((alert) => (
        <article key={`${alert.title}-${alert.dueDate ?? "na"}`} className={`alert-item ${alert.severity}`}>
          <div>
            <div className={`pill ${alert.severity}`}>{alert.severity.toUpperCase()}</div>
            <h4 style={{ marginBottom: 8 }}>{alert.title}</h4>
            <div className="kpi-description">{alert.message}</div>
          </div>
          <div style={{ textAlign: "right", minWidth: 120 }}>
            {alert.amount !== undefined ? <strong>{formatCurrency(alert.amount)}</strong> : null}
            {alert.dueDate ? <div className="kpi-description">{alert.dueDate}</div> : null}
          </div>
        </article>
      ))}
    </div>
  );
}

export function MetricTable({ metrics }: Readonly<{ metrics: Metric[] }>) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Metric</th>
          <th>Value</th>
          <th>Unit</th>
        </tr>
      </thead>
      <tbody>
        {metrics.map((metric) => (
          <tr key={metric.key}>
            <td>{metric.label}</td>
            <td>{metric.unit === "money" ? formatCurrency(Number(metric.value)) : formatValue(metric.value, metric.unit)}</td>
            <td>{metric.unit}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
