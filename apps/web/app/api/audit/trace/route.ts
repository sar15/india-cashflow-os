import { NextRequest, NextResponse } from "next/server";

import { getApiTokenForSession, getSessionFromRequest } from "@/lib/auth";
import { getApiBaseUrl, getApiRequestHeaders } from "@/lib/api";

export async function GET(request: NextRequest) {
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
      { error: "Set API_BASE_URL or NEXT_PUBLIC_API_BASE_URL to enable chart drill-down." },
      { status: 503 }
    );
  }

  const reportId = request.nextUrl.searchParams.get("reportId");
  const chartId = request.nextUrl.searchParams.get("chartId");
  const pointKey = request.nextUrl.searchParams.get("pointKey");

  if (!reportId || !chartId) {
    return NextResponse.json(
      { error: "reportId and chartId are required." },
      { status: 400 }
    );
  }

  const searchParams = new URLSearchParams();
  if (pointKey) {
    searchParams.set("point_key", pointKey);
  }

  const response = await fetch(
    `${apiBase}/v1/reports/${encodeURIComponent(reportId)}/charts/${encodeURIComponent(chartId)}/trace?${searchParams.toString()}`,
    {
      cache: "no-store",
      headers: getApiRequestHeaders(undefined, apiToken)
    }
  );

  const payload = await response.json().catch(() => ({ error: "Unable to parse trace response." }));
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }

  return NextResponse.json(payload, {
    headers: {
      "cache-control": "no-store"
    }
  });
}
