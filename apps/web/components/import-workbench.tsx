"use client";

import { useRouter } from "next/navigation";
import { useState, useRef } from "react";

const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set([".csv", ".xlsx", ".xls", ".xml", ".json"]);

function getFileExtension(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 ? filename.slice(dot).toLowerCase() : "";
}

type ParseErrorDetail = {
  message?: string;
  error_code?: string;
  filename?: string | null;
  row?: number | null;
  column?: string | null;
};

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
  const router = useRouter();
  const [sourceType, setSourceType] = useState("manual");
  const [sourceHint, setSourceHint] = useState("receivables");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function validateFile(file: File): string | null {
    const ext = getFileExtension(file.name);
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      return `Unsupported file type "${ext}". Accepted formats: ${[...ALLOWED_EXTENSIONS].sort().join(", ")}`;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File is too large (${(file.size / (1024 * 1024)).toFixed(1)} MB).`;
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

  function handleDrag(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      setSelectedFile(file);
    }
  }

  async function runImport(useDemo: boolean) {
    setError(null);
    if (!useDemo && !selectedFile) {
        setError("Please select a file to upload.");
        return;
    }
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
        setIsSubmitting(false);
        return;
      }

      router.push(`/setup?importBatchId=${encodeURIComponent(payload.import_batch.import_batch_id)}`);
    } catch (err) {
      setError("An unexpected network error occurred.");
      setIsSubmitting(false);
    }
  }

  return (
    <section className="section-card" style={{ width: "100%", maxWidth: 800, margin: "0 auto" }}>
      <div className="card-header">
        <div>
          <h3 className="card-title">Run an import</h3>
          <p className="card-subtitle">Drop your Tally or manual export to begin the forecast generation process.</p>
        </div>
        <span className="pill">Live flow</span>
      </div>

      <div className="control-grid" style={{ marginBottom: 24 }}>
        <label className="field">
          <span>Source type</span>
          <select className="input" value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
            <option value="manual">Manual Template</option>
            <option value="tally">Tally Export</option>
          </select>
        </label>

        <label className="field">
          <span>Tally source hint (if Tally)</span>
          <select className="input" value={sourceHint} onChange={(event) => setSourceHint(event.target.value)}>
            <option value="receivables">Receivables</option>
            <option value="payables">Payables</option>
          </select>
        </label>
      </div>

      <div 
        className={`drop-zone ${dragActive ? 'active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragActive ? 'var(--accent-color)' : 'var(--border-color)'}`,
          borderRadius: 12,
          padding: 64,
          textAlign: "center",
          cursor: "pointer",
          backgroundColor: dragActive ? 'rgba(0,0,0,0.4)' : 'rgba(0,0,0,0.2)',
          transition: "all 0.2s ease"
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.xml,.json"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
        <div style={{ fontSize: "2rem", marginBottom: 16 }}>📁</div>
        <h3 style={{ margin: "0 0 8px" }}>Drag & Drop your file here</h3>
        <p className="kpi-description">Or click to browse files (.csv, .xlsx, .xml, .json up to {MAX_FILE_SIZE_MB}MB)</p>
        
        {selectedFile && (
          <div style={{ marginTop: 24, padding: "12px 24px", background: "var(--bg-elevated)", borderRadius: 8, display: "inline-block" }}>
            <span style={{ fontWeight: 500 }}>Selected: {selectedFile.name}</span>
            <button 
              onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
              style={{ marginLeft: 12, background: "none", border: "none", color: "var(--error-text)", cursor: "pointer" }}
            >
              ✕
            </button>
          </div>
        )}
      </div>

      <div className="inline-actions" style={{ marginTop: 32, justifyContent: "center" }}>
        <button className="button" disabled={isSubmitting || !selectedFile} onClick={() => void runImport(false)} style={{ padding: "12px 32px", fontSize: "1.1rem" }}>
          {isSubmitting ? "Uploading..." : "Upload & Continue"}
        </button>
        <button className="button secondary" disabled={isSubmitting} onClick={() => void runImport(true)}>
          Use Demo Dataset
        </button>
      </div>

      {error ? (
        <div className="status-copy error" style={{ whiteSpace: "pre-wrap", marginTop: 24, textAlign: "center" }}>
          {error}
        </div>
      ) : null}
    </section>
  );
}
