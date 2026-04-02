import { NextRequest, NextResponse } from "next/server";
import { getApiTokenForSession, getSessionFromRequest } from "@/lib/auth";
import { getApiBaseUrl, getApiRequestHeaders } from "@/lib/api";

type RouteParams = { params: Promise<{ id: string }> };

export async function GET(request: NextRequest, props: RouteParams) {
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
      { error: "Set API_BASE_URL to enable imports." },
      { status: 503 }
    );
  }

  const { id } = await props.params;

  const response = await fetch(`${apiBase}/v1/imports/${encodeURIComponent(id)}`, {
    headers: getApiRequestHeaders(undefined, apiToken)
  });

  const payload = await response.json();
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  return NextResponse.json(payload);
}
