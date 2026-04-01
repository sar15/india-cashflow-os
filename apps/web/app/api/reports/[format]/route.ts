import { NextRequest, NextResponse } from "next/server";

import { getApiTokenForSession, getSessionFromRequest } from "@/lib/auth";
import { getApiBaseUrl, getApiRequestHeaders } from "@/lib/api";

const downloadContentTypes = {
  pdf: "application/pdf",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
} as const;

type ReportFormat = keyof typeof downloadContentTypes;

function isReportFormat(value: string): value is ReportFormat {
  return value === "pdf" || value === "xlsx";
}

async function fetchDemoForecastRunId(apiBase: string, apiToken: string) {
  const response = await fetch(`${apiBase}/v1/dashboards/cash?demo=1`, {
    cache: "no-store",
    headers: getApiRequestHeaders(undefined, apiToken)
  });
  if (!response.ok) {
    return null;
  }
  const payload = await response.json();
  return payload.forecast_run?.forecast_run_id ?? null;
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ format: string }> }
) {
  const session = getSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({ error: "Sign in is required." }, { status: 401 });
  }

  const apiToken = getApiTokenForSession(session);
  if (!apiToken) {
    return NextResponse.json({ error: "No API token is configured for this user." }, { status: 403 });
  }

  const { format } = await context.params;
  if (!isReportFormat(format)) {
    return NextResponse.json({ error: "Unsupported report format." }, { status: 400 });
  }

  const apiBase = getApiBaseUrl();
  if (!apiBase) {
    return NextResponse.json(
      { error: "Set API_BASE_URL or NEXT_PUBLIC_API_BASE_URL to enable report generation." },
      { status: 503 }
    );
  }

  let forecastRunId = request.nextUrl.searchParams.get("forecastRunId");
  if (!forecastRunId || forecastRunId === "demo") {
    forecastRunId = await fetchDemoForecastRunId(apiBase, apiToken);
  }
  if (!forecastRunId) {
    return NextResponse.json({ error: "Unable to resolve a forecast run for export." }, { status: 502 });
  }

  const reportResponse = await fetch(`${apiBase}/v1/reports`, {
    method: "POST",
    headers: getApiRequestHeaders(
      {
      "content-type": "application/json"
      },
      apiToken
    ),
    body: JSON.stringify({
      forecast_run_id: forecastRunId,
      include_scenarios: true
    }),
    cache: "no-store"
  });
  if (!reportResponse.ok) {
    return NextResponse.json({ error: "Unable to create the report pack." }, { status: 502 });
  }

  const report = await reportResponse.json();
  const downloadResponse = await fetch(
    `${apiBase}/v1/reports/${report.report_id}/download?format=${format}`,
    {
      cache: "no-store",
      headers: getApiRequestHeaders(undefined, apiToken)
    }
  );
  if (!downloadResponse.ok) {
    return NextResponse.json({ error: "Unable to download the generated report." }, { status: 502 });
  }

  const bytes = await downloadResponse.arrayBuffer();
  return new NextResponse(bytes, {
    headers: {
      "cache-control": "no-store",
      "content-disposition": `attachment; filename="cashflow-pack.${format}"`,
      "content-type": downloadContentTypes[format]
    }
  });
}
