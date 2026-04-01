import { NextRequest, NextResponse } from "next/server";

import { getApiTokenForSession, getSessionFromRequest } from "@/lib/auth";
import { getApiBaseUrl, getApiRequestHeaders } from "@/lib/api";

type SetupRequestPayload = {
  importBatchId?: string;
  companyName?: string;
  industry?: string;
  asOfDate?: string;
  openingBalanceInr?: string;
  minimumCashBufferInr?: string;
  obligations?: Array<{
    name?: string;
    obligationType?: string;
    frequency?: string;
    amountInr?: string;
    dueDay?: string;
    startDate?: string;
    notes?: string;
  }>;
  scenario?: {
    name?: string;
    description?: string;
    inflowDelayDays?: string;
    outflowDelayDays?: string;
    inflowScalarPercent?: string;
    outflowScalarPercent?: string;
    openingCashAdjustmentInr?: string;
  };
};

function toMinorUnits(value: unknown) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) {
    return undefined;
  }
  return Math.round(numeric * 100);
}

function toBasisPoints(value: unknown) {
  const numeric = Number(value ?? 100);
  if (!Number.isFinite(numeric)) {
    return 10000;
  }
  return Math.round(numeric * 100);
}

export async function POST(request: NextRequest) {
  const session = getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ error: "Sign in is required." }, { status: 401 });
  }

  const apiToken = getApiTokenForSession(session);
  if (!apiToken) {
    return NextResponse.json({ error: "No API token is configured for this user." }, { status: 403 });
  }

  const apiBase = getApiBaseUrl();
  if (!apiBase) {
    return NextResponse.json(
      { error: "Set API_BASE_URL or NEXT_PUBLIC_API_BASE_URL to enable onboarding." },
      { status: 503 }
    );
  }

  const payload = (await request.json()) as SetupRequestPayload;
  const importBatchId = String(payload.importBatchId ?? "").trim();
  if (!importBatchId) {
    return NextResponse.json({ error: "Import batch ID is required." }, { status: 400 });
  }

  const configuredObligations = Array.isArray(payload.obligations)
    ? payload.obligations
        .map((item) => ({
          name: String(item?.name ?? "").trim(),
          obligation_type: String(item?.obligationType ?? "other"),
          frequency: String(item?.frequency ?? "monthly"),
          amount_minor_units: toMinorUnits(item?.amountInr) ?? 0,
          due_day: item?.dueDay === "" || item?.dueDay === undefined ? undefined : Number(item?.dueDay),
          start_date: String(item?.startDate ?? payload.asOfDate),
          notes: String(item?.notes ?? "").trim() || undefined
        }))
        .filter((item) => item.name && item.amount_minor_units > 0)
    : [];

  const scenario =
    payload.scenario && typeof payload.scenario === "object"
      ? {
          name: String(payload.scenario.name ?? "Base Case").trim() || "Base Case",
          description: String(payload.scenario.description ?? "").trim() || undefined,
          inflow_delay_days: Number(payload.scenario.inflowDelayDays ?? 0) || 0,
          outflow_delay_days: Number(payload.scenario.outflowDelayDays ?? 0) || 0,
          inflow_scalar_bps: toBasisPoints(payload.scenario.inflowScalarPercent),
          outflow_scalar_bps: toBasisPoints(payload.scenario.outflowScalarPercent),
          opening_cash_adjustment_minor_units: toMinorUnits(payload.scenario.openingCashAdjustmentInr) ?? 0
        }
      : undefined;

  const confirmResponse = await fetch(`${apiBase}/v1/imports/${encodeURIComponent(importBatchId)}/confirm-mapping`, {
    method: "POST",
    headers: getApiRequestHeaders(
      {
      "content-type": "application/json"
      },
      apiToken
    ),
    body: JSON.stringify({
      company_name: payload.companyName,
      industry: payload.industry,
      as_of_date: payload.asOfDate,
      opening_balance_minor_units: payload.openingBalanceInr === "" ? undefined : toMinorUnits(payload.openingBalanceInr),
      minimum_cash_buffer_minor_units: toMinorUnits(payload.minimumCashBufferInr) ?? 0,
      scenario,
      obligations: configuredObligations
    }),
    cache: "no-store"
  });
  const confirmPayload = await confirmResponse.json();
  if (!confirmResponse.ok) {
    return NextResponse.json(confirmPayload, { status: confirmResponse.status });
  }

  const runResponse = await fetch(`${apiBase}/v1/forecast-runs`, {
    method: "POST",
    headers: getApiRequestHeaders(
      {
      "content-type": "application/json"
      },
      apiToken
    ),
    body: JSON.stringify(confirmPayload),
    cache: "no-store"
  });
  const runPayload = await runResponse.json();
  if (!runResponse.ok) {
    return NextResponse.json(runPayload, { status: runResponse.status });
  }

  return NextResponse.json({
    forecastRunId: runPayload.forecast_run_id,
    forecastRun: runPayload
  });
}
