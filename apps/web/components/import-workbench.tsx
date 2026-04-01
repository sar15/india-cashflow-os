"use client";

import Link from "next/link";
import { useState } from "react";

import { formatCurrency } from "@/lib/formatters";

const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set([".csv", ".xlsx", ".xls", ".xml", ".json"]);

function getFileExtension(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 ? filename.slice(dot).toLowerCase() : "";
}

type ImportIssue = {
  issue_id: string;
  severity: string;
  message: string;
  field_name?: string | null;
  row_number?: number | null;
};

type ImportCounterparty = {
  counterparty_id: string;
  entity_name: string;
  relationship_type: string;
  is_msme_registered: boolean;
  behavioral_delay_days: number;
  collection_confidence: number;
};

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

type ImportObligation = {
  obligation_id: string;
  name: string;
  obligation_type: string;
  frequency: string;
  amount_minor_units: number;
  due_day?: number | null;
  start_date: string;
};

type ImportResult = {
  import_batch: {
    import_batch_id: string;
    source_type: string;
    filename: string;
    event_count: number;
    counterparty_count: number;
    obligation_count: number;
    unresolved_issues: ImportIssue[];
  };
  bank_balance?: {
    account_name: string;
    balance_minor_units: number;
    as_of_date: string;
  } | null;
  inventory_snapshot?: {
    inventory_minor_units: number;
    raw_material_cover_days?: number | null;
  } | null;
  counterparties: ImportCounterparty[];
  events: ImportEvent[];
  obligations: ImportObligation[];
};

type ParseErrorDetail = {
  message?: string;
  error_code?: string;
  filename?: string | null;
  row?: number | null;
  column?: string | null;
};

function formatDelay(days: number) {
  if (!days) {
    return "On-time";
  }
  return `${days}d expected delay`;
}

function formatConfidence(confidence: number) {
  return `${Math.round(confidence * 100)}% confidence`;
}

function formatErrorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const parsed = detail as ParseErrorDetail;
    const parts: string[] = [];
    if (parsed.row) parts.push(`Row ${parsed.row}`);
    if (parsed.column) parts.push(`Column: ${parsed.column}`);
    if (parsed.message) parts.push(parsed.message);
    if (parts.length > 0) return parts.join(" · ");
    if (parsed.filename) return `Error parsing ${parsed.filename}`;
  }
  return "Import failed. Please check your file and try again.";
}

export function ImportWorkbench() {
  const [sourceType, setSourceType] = useState("manual");
  const [sourceHint, setSourceHint] = useState("receivables");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validateFile(file: File): string | null {
    const ext = getFileExtension(file.name);
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      return `Unsupported file type "${ext}". Accepted formats: ${[...ALLOWED_EXTENSIONS].sort().join(", ")}`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File is too large (${(file.size / (1024 * 1024)).toFixed(1)} MB). Maximum allowed size is ${MAX_FILE_SIZE_MB} MB.`;
    }
    return null;
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setError(null);
    if (file) {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        setSelectedFile(null);
        return;
      }
    }
    setSelectedFile(file);
  }

  async function runImport(useDemo: boolean) {
    setError(null);
    setResult(null);

    if (!useDemo && selectedFile) {
      const validationError = validateFile(selectedFile);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.set("sourceType", sourceType);
      formData.set("sourceHint", sourceHint);
      formData.set("useDemo", String(useDemo));
      if (!useDemo && selectedFile) {
        formData.set("file", selectedFile, selectedFile.name);
      }

      const response = await fetch("/api/imports", {
        method: "POST",
        body: formData
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(formatErrorMessage(payload.detail ?? payload.error));
        return;
      }
      setResult(payload);
    } finally {
      setIsSubmitting(false);
    }
  }

  const eventCount = result?.import_batch.event_count ?? result?.events.length ?? 0;
  const counterpartyCount = result?.import_batch.counterparty_count ?? result?.counterparties.length ?? 0;
  const obligationCount = result?.import_batch.obligation_count ?? result?.obligations.length ?? 0;
  const previewEvents = result?.events.slice(0, 5) ?? [];
  const previewCounterparties = result?.counterparties.slice(0, 4) ?? [];
  const previewObligations = result?.obligations.slice(0, 4) ?? [];

  return (
    <section className="section-card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Run an import</h3>
          <p className="card-subtitle">Start with a demo dataset or upload a source file, then review only the items that affect forecast trust.</p>
        </div>
        <span className="pill">Live flow</span>
      </div>

      <div className="control-grid">
        <label className="field">
          <span>Source type</span>
          <select className="input" value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
            <option value="manual">Manual Template</option>
            <option value="tally">Tally Export</option>
            <option value="zoho">Zoho Books Export</option>
          </select>
        </label>

        <label className="field">
          <span>Source hint</span>
          <select className="input" value={sourceHint} onChange={(event) => setSourceHint(event.target.value)}>
            <option value="receivables">Receivables</option>
            <option value="payables">Payables</option>
          </select>
        </label>

        <label className="field">
          <span>Upload file <span style={{ opacity: 0.5, fontSize: "0.85em" }}>(.csv, .xlsx, .xml, .json — max {MAX_FILE_SIZE_MB}MB)</span></span>
          <input
            className="input"
            type="file"
            accept=".csv,.xlsx,.xls,.xml,.json"
            onChange={handleFileChange}
          />
        </label>

        <label className="field">
          <span>Selected file</span>
          <input className="input" value={selectedFile?.name ?? "Demo import will use the seeded bundle"} readOnly />
        </label>
      </div>

      <div className="inline-actions">
        <button className="button" disabled={isSubmitting} onClick={() => void runImport(true)}>
          {isSubmitting ? "Working..." : "Load Demo Import"}
        </button>
        <button className="button secondary" disabled={isSubmitting || !selectedFile} onClick={() => void runImport(false)}>
          Upload Selected File
        </button>
        <a href="/api/templates/download" className="button secondary" download style={{ textDecoration: "none" }}>
          ↓ Download Template
        </a>
      </div>

      {error ? (
        <div className="status-copy error" style={{ whiteSpace: "pre-wrap" }}>
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="result-card">
          <div className="source-list">
            <div className="source-item">
              <strong>Import batch</strong>
              <span className="kpi-description">{result.import_batch.import_batch_id}</span>
            </div>
            <div className="source-item">
              <strong>Source</strong>
              <span className="kpi-description">{result.import_batch.source_type.toUpperCase()} · {result.import_batch.filename}</span>
            </div>
            <div className="source-item">
              <strong>Events parsed</strong>
              <span className="kpi-description">{eventCount}</span>
            </div>
            <div className="source-item">
              <strong>Counterparties</strong>
              <span className="kpi-description">{counterpartyCount}</span>
            </div>
            <div className="source-item">
              <strong>Recurring obligations</strong>
              <span className="kpi-description">{obligationCount}</span>
            </div>
            <div className="source-item">
              <strong>Issues to review</strong>
              <span className="kpi-description">{result.import_batch.unresolved_issues.length}</span>
            </div>
          </div>

          {result.import_batch.unresolved_issues.length ? (
            <div className="alert-list">
              {result.import_batch.unresolved_issues.map((issue) => (
                <article key={issue.issue_id} className={`alert-item ${issue.severity}`}>
                  <div>
                    <h4 style={{ margin: "0 0 8px" }}>{issue.severity.toUpperCase()}</h4>
                    <div className="kpi-description">{issue.message}</div>
                    {issue.field_name || issue.row_number ? (
                      <div className="kpi-description">
                        {[issue.field_name ? `Field: ${issue.field_name}` : null, issue.row_number ? `Row: ${issue.row_number}` : null]
                          .filter(Boolean)
                          .join(" · ")}
                      </div>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="status-copy success">No blocking issues were found. The import is ready for cash rules and forecast creation.</div>
          )}

          <div className="two-column">
            <article className="source-card">
              <h3>Opening position</h3>
              <div className="source-list">
                <div className="source-item">
                  <strong>Bank balance</strong>
                  <span className="kpi-description">
                    {result.bank_balance ? `${formatCurrency(result.bank_balance.balance_minor_units / 100)} · ${result.bank_balance.as_of_date}` : "Not provided"}
                  </span>
                </div>
                <div className="source-item">
                  <strong>Inventory snapshot</strong>
                  <span className="kpi-description">
                    {result.inventory_snapshot ? formatCurrency(result.inventory_snapshot.inventory_minor_units / 100) : "Not provided"}
                  </span>
                </div>
                <div className="source-item">
                  <strong>Raw-material cover</strong>
                  <span className="kpi-description">
                    {result.inventory_snapshot?.raw_material_cover_days ? `${result.inventory_snapshot.raw_material_cover_days} days` : "Not provided"}
                  </span>
                </div>
              </div>
            </article>

            <article className="source-card">
              <h3>Counterparty signals</h3>
              <div className="source-list">
                {previewCounterparties.length ? (
                  previewCounterparties.map((counterparty) => (
                    <div key={counterparty.counterparty_id} className="source-item">
                      <div>
                        <strong>{counterparty.entity_name}</strong>
                        <div className="kpi-description">
                          {counterparty.relationship_type} · {formatDelay(counterparty.behavioral_delay_days)}
                        </div>
                      </div>
                      <div className="kpi-description" style={{ textAlign: "right" }}>
                        {formatConfidence(counterparty.collection_confidence)}
                        {counterparty.is_msme_registered ? " · MSME" : ""}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="status-copy">No counterparties were parsed from this import.</div>
                )}
              </div>
            </article>
          </div>

          <article className="source-card">
            <h3>Event preview</h3>
            {previewEvents.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Counterparty</th>
                    <th>Type</th>
                    <th>Due</th>
                    <th>Status</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {previewEvents.map((event) => (
                    <tr key={event.event_id}>
                      <td>{event.document_number}</td>
                      <td>{event.counterparty_name ?? "Unassigned"}</td>
                      <td>{event.entity_type}</td>
                      <td>{event.expected_cash_date ?? event.due_date ?? "Needs date"}</td>
                      <td>{event.status}</td>
                      <td>{formatCurrency(event.net_minor_units / 100)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="status-copy">No cash events were parsed from this import.</div>
            )}
          </article>

          <article className="source-card">
            <h3>Recurring obligations found</h3>
            {previewObligations.length ? (
              <div className="source-list">
                {previewObligations.map((obligation) => (
                  <div key={obligation.obligation_id} className="source-item">
                    <div>
                      <strong>{obligation.name}</strong>
                      <div className="kpi-description">
                        {obligation.obligation_type} · {obligation.frequency} · starts {obligation.start_date}
                      </div>
                    </div>
                    <div className="kpi-description" style={{ textAlign: "right" }}>
                      {formatCurrency(obligation.amount_minor_units / 100)}
                      {obligation.due_day ? ` · day ${obligation.due_day}` : ""}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="status-copy">No recurring obligations were embedded in this import.</div>
            )}
          </article>

          <div className="inline-actions">
            <Link className="button" href={`/setup?importBatchId=${encodeURIComponent(result.import_batch.import_batch_id)}`}>
              Continue to Cash Rules
            </Link>
          </div>
        </div>
      ) : null}
    </section>
  );
}
