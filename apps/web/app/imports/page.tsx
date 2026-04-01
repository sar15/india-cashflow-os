import { AppShell } from "@/components/app-shell";
import { ImportWorkbench } from "@/components/import-workbench";

const sources = [
  {
    title: "Tally exports",
    body: "Outstanding ledgers, debtors, creditors, day book, and trial balance imports are the fastest route for most Indian SMEs.",
    details: "Deterministic parsing first, AI fallback later only when confidence is low."
  },
  {
    title: "Zoho Books export",
    body: "Upload your Zoho Books JSON export. Invoice, bill, contact, and payment data is parsed automatically.",
    details: "Export from Zoho Books → Upload the JSON file → Review and confirm."
  },
  {
    title: "Manual template",
    body: "A clean workbook keeps onboarding fast when source systems are messy or the accountant only wants a controlled upload shape.",
    details: "Download our template, fill in your data, and upload."
  }
];

const reviewPrinciples = [
  "Missing schedule dates that would otherwise force a silent timing guess",
  "Low-confidence mappings where the source label does not clearly map to a customer, vendor, or obligation",
  "Already overdue items that will be rolled into forecast day 1 unless the team intervenes",
  "Counterparties with weak collections confidence or MSME sensitivity that deserve extra attention"
];

export default async function ImportsPage() {
  return (
    <AppShell activePath="/imports">
      <section className="hero-card">
        <span className="eyebrow">Step 1 · Upload Your Data</span>
        <h1 className="page-title">Upload your Tally, Zoho, or manual export and get a 13-week cashflow forecast.</h1>
        <p>
          Drop your Excel, CSV, or JSON export below. The platform parses it, flags anything that needs your review,
          and moves straight into rules and forecast generation.
        </p>
        <div className="page-actions">
          <a href="/api/templates/download" className="button secondary" download>
            ↓ Download Standard Template
          </a>
        </div>
      </section>

      <section className="three-column">
        {sources.map((source) => (
          <article key={source.title} className="source-card">
            <h3>{source.title}</h3>
            <p>{source.body}</p>
            <div className="kpi-description">{source.details}</div>
          </article>
        ))}
      </section>

      <section className="two-column">
        <ImportWorkbench />

        <article className="section-card">
          <div className="card-header">
            <div>
              <h3 className="card-title">What gets flagged</h3>
              <p className="card-subtitle">The review queue stays narrow on purpose so teams spend time only on issues that change forecast trust.</p>
            </div>
            <span className="pill warning">Review queue</span>
          </div>
          <div className="alert-list">
            {reviewPrinciples.map((item) => (
              <article key={item} className="alert-item warning">
                <div>
                  <h4 style={{ margin: "0 0 8px" }}>{item}</h4>
                  <div className="kpi-description">User action is requested only when the engine would otherwise make an assumption that should stay explicit.</div>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>
    </AppShell>
  );
}
