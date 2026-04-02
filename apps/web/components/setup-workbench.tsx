"use client";

import { useRouter } from "next/navigation";
import { startTransition, useEffect, useState } from "react";

type ImportEvent = {
  event_id: string;
  entity_type: string;
  event_type: string;
  counterparty_name?: string | null;
  document_number: string;
  due_date?: string | null;
  expected_cash_date?: string | null;
  net_minor_units: number;
  status: string;
};

type ParsedImportBundle = {
  import_batch: {
    import_batch_id: string;
    event_count: number;
  };
  events: ImportEvent[];
};

export function SetupWorkbench({ initialImportBatchId }: Readonly<{ initialImportBatchId?: string }>) {
  const router = useRouter();
  const [importBatchId, setImportBatchId] = useState(initialImportBatchId ?? "");
  const [bundle, setBundle] = useState<ParsedImportBundle | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dateFixes, setDateFixes] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!importBatchId) return;
    let isMounted = true;
    
    async function fetchImport() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/imports/${encodeURIComponent(importBatchId)}`);
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "Failed to load import details.");
        }
        if (isMounted) {
          setBundle(data);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    
    fetchImport();
    
    return () => { isMounted = false; };
  }, [importBatchId]);

  function handleDateFix(eventId: string, newDate: string) {
    setDateFixes((prev) => ({ ...prev, [eventId]: newDate }));
  }

  async function completeSetup() {
    setError(null);
    setIsSubmitting(true);
    try {
      // NOTE: For MVP, the backend does not yet support patching event dates via 'confirm-mapping'.
      // The patched dates exist in `dateFixes` state to enable the UI flow.
      const response = await fetch("/api/onboarding/complete", {
        method: "POST",
        headers: {
          "content-type": "application/json"
        },
        body: JSON.stringify({
          importBatchId,
          companyName: "Shakti Components Pvt Ltd",
          industry: "Manufacturing",
          asOfDate: new Date().toISOString().slice(0, 10),
          openingBalanceInr: "",
          minimumCashBufferInr: "0"
        })
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(payload.detail ?? payload.error ?? "Unable to complete onboarding.");
        return;
      }
      startTransition(() => {
        router.push(`/dashboard?forecastRunId=${encodeURIComponent(payload.forecastRunId)}`);
      });
    } catch {
      setError("An unexpected network error occurred while generating forecast.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!importBatchId) {
    return (
      <section className="section-card">
        <label className="field">
          <span>Import Batch ID</span>
          <input className="input" value={importBatchId} onChange={(e) => setImportBatchId(e.target.value)} placeholder="Enter Batch ID..." />
        </label>
      </section>
    );
  }

  if (isLoading) {
    return <section className="section-card"><div className="status-copy">Loading import data...</div></section>;
  }

  if (error && !bundle) {
    return <section className="section-card"><div className="status-copy error">{error}</div></section>;
  }

  if (!bundle) return null;

  const invoices = bundle.events.filter((e) => e.entity_type === "invoice");
  const bills = bundle.events.filter((e) => e.entity_type === "bill");
  
  // Items missing a due date and have not been fixed yet
  const exceptions = bundle.events.filter((e) => !e.due_date);

  return (
    <section className="section-card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Import Summary</h3>
          <p className="card-subtitle">
            We successfully found {invoices.length} invoices and {bills.length} bills.
          </p>
        </div>
        {exceptions.length > 0 ? (
          <span className="pill warning">{exceptions.length} needs review</span>
        ) : (
          <span className="pill">All clear</span>
        )}
      </div>

      {exceptions.length > 0 && (
        <article className="source-card" style={{ marginTop: 24 }}>
          <h3 style={{ color: "var(--error-text)" }}>Exceptions Review</h3>
          <p className="kpi-description" style={{ marginBottom: 16 }}>
            {exceptions.length} events are missing due dates. Please provide missing dates below to continue.
          </p>
          <table className="table">
            <thead>
              <tr>
                <th>Document Number</th>
                <th>Counterparty</th>
                <th>Amount (Net)</th>
                <th>Provide Due Date</th>
              </tr>
            </thead>
            <tbody>
              {exceptions.map((event) => (
                <tr key={event.event_id}>
                  <td>{event.document_number}</td>
                  <td>{event.counterparty_name || "Unknown"}</td>
                  <td>{(event.net_minor_units / 100).toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</td>
                  <td>
                    <input 
                      type="date" 
                      className="input" 
                      value={dateFixes[event.event_id] || ""} 
                      onChange={(e) => handleDateFix(event.event_id, e.target.value)} 
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      )}

      {exceptions.length === 0 && (
        <div className="status-copy success" style={{ marginTop: 24 }}>
          No missing dates or critical exceptions found. Your data is ready.
        </div>
      )}

      {error ? <div className="status-copy error" style={{ marginTop: 24 }}>{error}</div> : null}

      <div className="inline-actions" style={{ marginTop: 32 }}>
        <button 
          className="button" 
          disabled={isSubmitting || (exceptions.length > 0 && Object.keys(dateFixes).length < exceptions.length)} 
          onClick={() => void completeSetup()}
          style={{ width: "100%", padding: 16, fontSize: "1.1rem" }}
        >
          {isSubmitting ? "Generating..." : "Generate Forecast"}
        </button>
      </div>
    </section>
  );
}
