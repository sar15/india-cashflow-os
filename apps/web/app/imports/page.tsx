import { AppShell } from "@/components/app-shell";
import { ImportWorkbench } from "@/components/import-workbench";

const sources = [
  {
    title: "Tally exports",
    body: "Outstanding ledgers, debtors, creditors, day book, and trial balance imports are the fastest route for most Indian SMEs.",
    details: "Deterministic parsing first, AI fallback later only when confidence is low."
  },
  {
    title: "Zoho Books",
    body: "Cloud-native invoice, bill, contact, and payment payloads reduce mapping friction and improve refresh speed.",
    details: "The live OAuth handoff now returns into the import flow and can sync invoices and bills into a fresh batch."
  },
  {
    title: "Manual template",
    body: "A clean workbook keeps onboarding fast when source systems are messy or the accountant only wants a controlled upload shape.",
    details: "Best fallback for pilots and quick customer setup."
  }
];

const reviewPrinciples = [
  "Missing schedule dates that would otherwise force a silent timing guess",
  "Low-confidence mappings where the source label does not clearly map to a customer, vendor, or obligation",
  "Already overdue items that will be rolled into forecast day 1 unless the team intervenes",
  "Counterparties with weak collections confidence or MSME sensitivity that deserve extra attention"
];

export default async function ImportsPage({
  searchParams
}: Readonly<{ searchParams?: Promise<{ zoho?: string }> }>) {
  const params = searchParams ? await searchParams : undefined;
  const zohoStatusMessages: Record<string, { title: string; body: string; tone: "success" | "warning" | "error" }> = {
    connected: {
      title: "Zoho Books connected",
      body: "The OAuth handshake completed and the latest invoices and bills were pulled into a fresh import batch.",
      tone: "success"
    },
    unavailable: {
      title: "Zoho is not configured yet",
      body: "Set the Zoho OAuth environment variables and the API base URL before using the live Zoho connector.",
      tone: "warning"
    },
    not_configured: {
      title: "Zoho OAuth needs configuration",
      body: "The connector endpoint is reachable, but the Zoho client credentials or redirect URI are still missing.",
      tone: "warning"
    },
    connect_failed: {
      title: "Zoho connect request failed",
      body: "The app could not create a live Zoho authorization session. Check the API logs and try again.",
      tone: "error"
    },
    exchange_failed: {
      title: "Zoho authorization could not be completed",
      body: "Zoho returned to the app, but the code exchange failed before tokens could be stored.",
      tone: "error"
    },
    sync_failed: {
      title: "Zoho connected but sync failed",
      body: "The connector finished OAuth, but the first invoice and bill pull did not complete successfully.",
      tone: "error"
    },
    denied: {
      title: "Zoho access was cancelled",
      body: "The Zoho authorization step was closed or denied before the app received consent.",
      tone: "warning"
    },
    invalid_callback: {
      title: "Zoho callback was incomplete",
      body: "The callback was missing the state, code, or temporary connection ID needed to finish the import handoff.",
      tone: "error"
    }
  };
  const zohoStatus = params?.zoho ? zohoStatusMessages[params.zoho] : null;

  return (
    <AppShell activePath="/imports">
      <section className="hero-card">
        <span className="eyebrow">Step 1 · Connect or Upload</span>
        <h1 className="page-title">Ingestion is designed to feel guided, not technical.</h1>
        <p>
          The platform accepts hybrid input paths, but the experience stays minimal: import, review only unresolved items, and move
          straight into rules and forecast generation.
        </p>
        <div className="page-actions">
          <a href="/api/zoho/connect" className="button">
            Connect Zoho Books
          </a>
        </div>
      </section>

      {zohoStatus ? (
        <section className={`status-banner ${zohoStatus.tone}`}>
          <strong>{zohoStatus.title}</strong>
          <p>{zohoStatus.body}</p>
        </section>
      ) : null}

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

      <section className="section-card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Desktop sync pilot</h3>
            <p className="card-subtitle">Teams that prefer local-first setup can now run a lightweight folder watcher before deeper Tally integration lands.</p>
          </div>
          <span className="pill">Local beta</span>
        </div>
        <div className="step-flow">
          <article className="step-item">
            <div className="step-index">A</div>
            <div>
              <strong>Watch export folder</strong>
              <p>The desktop agent watches a chosen folder and uploads supported files through the existing authenticated import API.</p>
            </div>
          </article>
          <article className="step-item">
            <div className="step-index">B</div>
            <div>
              <strong>Signed sync health</strong>
              <p>Each machine registers with the API, sends heartbeats, and records the latest uploaded file so sync health stays explicit.</p>
            </div>
          </article>
        </div>
      </section>
    </AppShell>
  );
}
