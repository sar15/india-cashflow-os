import Link from "next/link";

import { AppShell } from "@/components/app-shell";

const steps = [
  {
    title: "Connect or Upload",
    body: "Upload Tally exports, Zoho Books exports, or a clean Excel template — no API integrations needed."
  },
  {
    title: "Review Exceptions Only",
    body: "Finance teams fix missing dates, mappings, and suspicious values instead of manually rebuilding the whole forecast."
  },
  {
    title: "Add Cash Rules",
    body: "Recurring obligations, compliance timing, cash buffers, and scenarios all sit in one deterministic rule layer."
  },
  {
    title: "Get Forecast",
    body: "Users land on a professional dashboard and can export a client-ready PDF or analyst-ready Excel pack."
  }
];

export default function HomePage() {
  return (
    <AppShell activePath="/">
      <section className="hero-card">
        <span className="eyebrow">Cash wedge first, broader FP&amp;A later</span>
        <div className="hero-grid">
          <div>
            <h1 className="hero-title">A weekly cash cockpit for Indian SMEs that turns messy finance data into decisions.</h1>
            <p>
              India Cashflow OS is designed for finance teams, promoters, and CA-supported workflows that need direct cash visibility,
              compliance-aware planning, and report-grade outputs without waiting for a perfect ERP environment.
            </p>
            <div className="page-actions">
              <Link href="/dashboard" className="button">
                View Forecast Dashboard
              </Link>
              <Link href="/imports" className="button secondary">
                Review Import Flow
              </Link>
            </div>
          </div>
          <div className="section-card">
            <h3>What this first release solves</h3>
            <div className="source-list">
              <div className="source-item">
                <strong>Short-horizon visibility</strong>
                <span className="kpi-description">13-week direct cash forecast</span>
              </div>
              <div className="source-item">
                <strong>India-native rules</strong>
                <span className="kpi-description">GST, TDS, EPF, EMI, payroll, MSME risk</span>
              </div>
              <div className="source-item">
                <strong>Auditability</strong>
                <span className="kpi-description">Every number tied back to an event and rule version</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="card-header">
          <div>
            <h2 className="card-title">The first user journey in four steps</h2>
            <p className="card-subtitle">The product is deliberately opinionated so finance teams reach a usable forecast in minimal steps.</p>
          </div>
          <span className="pill">4-step flow</span>
        </div>
        <div className="step-flow">
          {steps.map((step, index) => (
            <article key={step.title} className="step-item">
              <div className="step-index">{index + 1}</div>
              <div>
                <strong>{step.title}</strong>
                <p>{step.body}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="three-column">
        <article className="source-card">
          <h3>Direct cash method</h3>
          <p>The engine computes at daily granularity and aggregates weekly, which keeps the product aligned with real operating liquidity rather than long-horizon accrual optics.</p>
        </article>
        <article className="source-card">
          <h3>Professional reporting</h3>
          <p>The dashboard and exported packs use the same chart grammar and KPI vocabulary so teams do not lose trust between web, PDF, and Excel.</p>
        </article>
        <article className="source-card">
          <h3>Rule-first intelligence</h3>
          <p>AI is used around parsing and explanation. The math, scheduling rules, and compliance logic stay deterministic and fully traceable.</p>
        </article>
      </section>
    </AppShell>
  );
}

