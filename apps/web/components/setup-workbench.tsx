"use client";

import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";

import { formatCurrency } from "@/lib/formatters";

type DraftObligation = {
  name: string;
  obligationType: string;
  frequency: string;
  amountInr: string;
  dueDay: string;
  startDate: string;
  notes: string;
};

type ConfiguredObligation = DraftObligation & {
  id: string;
};

function toMinorUnits(value: string) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  return Math.round(numeric * 100);
}

function toBasisPoints(value: string) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 10000;
  }
  return Math.round(numeric * 100);
}

function buildEmptyDraft(asOfDate: string): DraftObligation {
  return {
    name: "",
    obligationType: "rent",
    frequency: "monthly",
    amountInr: "",
    dueDay: "",
    startDate: asOfDate,
    notes: ""
  };
}

export function SetupWorkbench({ initialImportBatchId }: Readonly<{ initialImportBatchId?: string }>) {
  const router = useRouter();
  const [importBatchId, setImportBatchId] = useState(initialImportBatchId ?? "");
  const [companyName, setCompanyName] = useState("Shakti Components Pvt Ltd");
  const [industry, setIndustry] = useState("Manufacturing");
  const [asOfDate, setAsOfDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [openingBalanceInr, setOpeningBalanceInr] = useState("");
  const [minimumCashBufferInr, setMinimumCashBufferInr] = useState("600000");
  const [scenarioName, setScenarioName] = useState("Base Case");
  const [scenarioDescription, setScenarioDescription] = useState("Confirmed after mapping review");
  const [inflowDelayDays, setInflowDelayDays] = useState("0");
  const [outflowDelayDays, setOutflowDelayDays] = useState("0");
  const [inflowScalarPercent, setInflowScalarPercent] = useState("100");
  const [outflowScalarPercent, setOutflowScalarPercent] = useState("100");
  const [openingCashAdjustmentInr, setOpeningCashAdjustmentInr] = useState("0");
  const [configuredObligations, setConfiguredObligations] = useState<ConfiguredObligation[]>([]);
  const [draftObligation, setDraftObligation] = useState<DraftObligation>(() => buildEmptyDraft(new Date().toISOString().slice(0, 10)));
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateDraftObligation(field: keyof DraftObligation, value: string) {
    setDraftObligation((current) => ({ ...current, [field]: value }));
  }

  function addObligation() {
    if (!draftObligation.name.trim()) {
      setError("Add a name for the recurring obligation before saving it.");
      return;
    }
    if (!draftObligation.amountInr.trim() || Number(draftObligation.amountInr) <= 0) {
      setError("Add a positive INR amount before saving the obligation.");
      return;
    }

    setConfiguredObligations((current) => [
      ...current,
      {
        ...draftObligation,
        dueDay: draftObligation.dueDay.trim(),
        id: crypto.randomUUID()
      }
    ]);
    setDraftObligation(buildEmptyDraft(asOfDate));
    setError(null);
  }

  function removeObligation(id: string) {
    setConfiguredObligations((current) => current.filter((item) => item.id !== id));
  }

  async function completeSetup() {
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/onboarding/complete", {
        method: "POST",
        headers: {
          "content-type": "application/json"
        },
        body: JSON.stringify({
          importBatchId,
          companyName,
          industry,
          asOfDate,
          openingBalanceInr,
          minimumCashBufferInr,
          scenario: {
            name: scenarioName,
            description: scenarioDescription,
            inflowDelayDays,
            outflowDelayDays,
            inflowScalarPercent,
            outflowScalarPercent,
            openingCashAdjustmentInr
          },
          obligations: configuredObligations
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
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="section-card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Confirm mapping and build forecast</h3>
          <p className="card-subtitle">This step now captures the real cash rules: opening position, minimum buffer, obligation layer, and scenario pressure.</p>
        </div>
        <span className="pill">Live flow</span>
      </div>

      <div className="control-grid">
        <label className="field">
          <span>Import batch ID</span>
          <input className="input" value={importBatchId} onChange={(event) => setImportBatchId(event.target.value)} />
        </label>

        <label className="field">
          <span>Company name</span>
          <input className="input" value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
        </label>

        <label className="field">
          <span>Industry</span>
          <input className="input" value={industry} onChange={(event) => setIndustry(event.target.value)} />
        </label>

        <label className="field">
          <span>As of date</span>
          <input className="input" type="date" value={asOfDate} onChange={(event) => setAsOfDate(event.target.value)} />
        </label>

        <label className="field">
          <span>Opening balance (INR)</span>
          <input className="input" value={openingBalanceInr} onChange={(event) => setOpeningBalanceInr(event.target.value)} placeholder="Optional override" />
        </label>

        <label className="field">
          <span>Minimum cash buffer (INR)</span>
          <input className="input" value={minimumCashBufferInr} onChange={(event) => setMinimumCashBufferInr(event.target.value)} />
        </label>
      </div>

      <div className="two-column" style={{ marginTop: 18 }}>
        <article className="source-card">
          <h3>Scenario tuning</h3>
          <div className="control-grid">
            <label className="field">
              <span>Scenario name</span>
              <input className="input" value={scenarioName} onChange={(event) => setScenarioName(event.target.value)} />
            </label>

            <label className="field">
              <span>Scenario description</span>
              <input className="input" value={scenarioDescription} onChange={(event) => setScenarioDescription(event.target.value)} />
            </label>

            <label className="field">
              <span>Inflow delay (days)</span>
              <input className="input" type="number" value={inflowDelayDays} onChange={(event) => setInflowDelayDays(event.target.value)} />
            </label>

            <label className="field">
              <span>Outflow delay (days)</span>
              <input className="input" type="number" value={outflowDelayDays} onChange={(event) => setOutflowDelayDays(event.target.value)} />
            </label>

            <label className="field">
              <span>Inflow realization (%)</span>
              <input className="input" type="number" step="0.1" value={inflowScalarPercent} onChange={(event) => setInflowScalarPercent(event.target.value)} />
            </label>

            <label className="field">
              <span>Outflow pressure (%)</span>
              <input className="input" type="number" step="0.1" value={outflowScalarPercent} onChange={(event) => setOutflowScalarPercent(event.target.value)} />
            </label>

            <label className="field">
              <span>Opening cash adjustment (INR)</span>
              <input className="input" value={openingCashAdjustmentInr} onChange={(event) => setOpeningCashAdjustmentInr(event.target.value)} />
            </label>
          </div>
          <div className="status-copy">
            Use this when collections are expected to slip, vendor pressure is higher than normal, or management wants a custom planning case before the dashboard is generated.
          </div>
        </article>

        <article className="source-card">
          <h3>Add recurring obligation</h3>
          <div className="control-grid">
            <label className="field">
              <span>Name</span>
              <input className="input" value={draftObligation.name} onChange={(event) => updateDraftObligation("name", event.target.value)} placeholder="Factory insurance" />
            </label>

            <label className="field">
              <span>Type</span>
              <select className="input" value={draftObligation.obligationType} onChange={(event) => updateDraftObligation("obligationType", event.target.value)}>
                <option value="rent">Rent</option>
                <option value="emi">EMI</option>
                <option value="payroll">Payroll</option>
                <option value="gst">GST</option>
                <option value="tds">TDS</option>
                <option value="epf">EPF</option>
                <option value="other">Other</option>
              </select>
            </label>

            <label className="field">
              <span>Frequency</span>
              <select className="input" value={draftObligation.frequency} onChange={(event) => updateDraftObligation("frequency", event.target.value)}>
                <option value="monthly">Monthly</option>
                <option value="weekly">Weekly</option>
                <option value="one_time">One time</option>
              </select>
            </label>

            <label className="field">
              <span>Amount (INR)</span>
              <input className="input" value={draftObligation.amountInr} onChange={(event) => updateDraftObligation("amountInr", event.target.value)} placeholder="25000" />
            </label>

            <label className="field">
              <span>Due day</span>
              <input className="input" type="number" value={draftObligation.dueDay} onChange={(event) => updateDraftObligation("dueDay", event.target.value)} placeholder="Optional for monthly" />
            </label>

            <label className="field">
              <span>Start date</span>
              <input className="input" type="date" value={draftObligation.startDate} onChange={(event) => updateDraftObligation("startDate", event.target.value)} />
            </label>

            <label className="field" style={{ gridColumn: "1 / -1" }}>
              <span>Notes</span>
              <input className="input" value={draftObligation.notes} onChange={(event) => updateDraftObligation("notes", event.target.value)} placeholder="Optional note for audit context" />
            </label>
          </div>
          <div className="inline-actions">
            <button className="button secondary" type="button" onClick={addObligation}>
              Add obligation
            </button>
          </div>
          <div className="status-copy">
            Leave due day blank to use the engine default for GST, TDS, EPF, payroll, EMI, or rent. One-time obligations use the start date directly.
          </div>
        </article>
      </div>

      {configuredObligations.length ? (
        <article className="source-card" style={{ marginTop: 18 }}>
          <h3>Configured obligations</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Frequency</th>
                <th>Start</th>
                <th>Amount</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {configuredObligations.map((obligation) => (
                <tr key={obligation.id}>
                  <td>{obligation.name}</td>
                  <td>{obligation.obligationType}</td>
                  <td>{obligation.frequency}</td>
                  <td>{obligation.startDate}</td>
                  <td>{formatCurrency(Number(obligation.amountInr))}</td>
                  <td>
                    <button className="button secondary" type="button" onClick={() => removeObligation(obligation.id)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ) : null}

      <div className="status-copy" style={{ marginTop: 18 }}>
        This forecast will use a scenario at {toBasisPoints(inflowScalarPercent) / 100}% inflow realization and {toBasisPoints(outflowScalarPercent) / 100}% outflow pressure, plus {configuredObligations.length} extra manual obligations.
      </div>

      <div className="inline-actions">
        <button className="button" disabled={isSubmitting || !importBatchId.trim()} onClick={() => void completeSetup()}>
          {isSubmitting ? "Creating Forecast..." : "Create Forecast Run"}
        </button>
      </div>

      {error ? <div className="status-copy error">{error}</div> : null}
    </section>
  );
}
