import { AppShell } from "@/components/app-shell";
import { SetupWorkbench } from "@/components/setup-workbench";

const obligations = [
  { label: "GST", due: "20th of the month", amount: "Configured in rules engine" },
  { label: "TDS", due: "7th of the month", amount: "Configured in rules engine" },
  { label: "EPF", due: "15th of the month", amount: "Configured in rules engine" },
  { label: "Payroll", due: "1st of the month", amount: "Recurring obligation" },
  { label: "EMI / Rent", due: "User-defined day", amount: "Recurring obligation" }
];

const scenarios = [
  {
    title: "Base Case",
    body: "Uses due dates, known counterparty delays, and the active cash buffer."
  },
  {
    title: "Stress Case",
    body: "Adds collection delays, inflow haircut, and slightly heavier outflow pressure."
  },
  {
    title: "Upside Case",
    body: "Improves collections and lets some planned outflows slip later."
  }
];

export default async function SetupPage({
  searchParams
}: Readonly<{ searchParams?: Promise<{ importBatchId?: string }> }>) {
  const params = searchParams ? await searchParams : undefined;

  return (
    <AppShell activePath="/setup">
      <section className="hero-card">
        <span className="eyebrow">Step 3 · Add Cash Rules</span>
        <h1 className="page-title">Finance rules, not hidden AI guesses, determine the first forecast.</h1>
        <p>
          Recurring obligations, scenario pressure, buffers, and statutory calendars are explicit inputs. The platform can explain why
          every amount lands where it does.
        </p>
      </section>

      <section className="two-column">
        <SetupWorkbench initialImportBatchId={params?.importBatchId} />

        <article className="section-card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Recurring obligation layer</h3>
              <p className="card-subtitle">India-specific due dates live in a deterministic rule engine, with manual override when needed.</p>
            </div>
            <span className="pill">Audit-ready</span>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Obligation</th>
                <th>Default timing</th>
                <th>How it behaves</th>
              </tr>
            </thead>
            <tbody>
              {obligations.map((obligation) => (
                <tr key={obligation.label}>
                  <td>{obligation.label}</td>
                  <td>{obligation.due}</td>
                  <td>{obligation.amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Scenario layer</h3>
            <p className="card-subtitle">Base, stress, and upside all run on the same event set so comparisons stay trustworthy.</p>
          </div>
          <span className="pill">What-if ready</span>
        </div>
        <div className="source-list">
          {scenarios.map((scenario) => (
            <article key={scenario.title} className="source-item">
              <div>
                <strong>{scenario.title}</strong>
                <div className="kpi-description">{scenario.body}</div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
