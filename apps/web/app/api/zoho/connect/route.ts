import { NextRequest, NextResponse } from "next/server";

import { getApiTokenForSession, getSessionFromRequest } from "@/lib/auth";
import { getApiBaseUrl, getApiRequestHeaders } from "@/lib/api";

const ZOHO_CONNECTION_COOKIE = "cashflow_zoho_connection_id";

export async function GET(request: NextRequest) {
  const session = getSessionFromRequest(request);
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const apiToken = getApiTokenForSession(session);
  const apiBase = getApiBaseUrl();
  if (!apiToken || !apiBase) {
    return NextResponse.redirect(new URL("/imports?zoho=unavailable", request.url));
  }

  const redirectUri = new URL("/auth/zoho/callback", request.url).toString();
  const response = await fetch(`${apiBase}/v1/sources/zoho/connect`, {
    method: "POST",
    cache: "no-store",
    headers: getApiRequestHeaders(
      {
        "content-type": "application/json"
      },
      apiToken
    ),
    body: JSON.stringify({
      org_id: session.orgId,
      redirect_uri: redirectUri
    })
  });

  if (!response.ok) {
    return NextResponse.redirect(new URL("/imports?zoho=connect_failed", request.url));
  }

  const payload = (await response.json()) as { auth_url?: string; connection_id?: string };
  if (!payload.auth_url || !payload.connection_id) {
    return NextResponse.redirect(new URL("/imports?zoho=not_configured", request.url));
  }

  const redirectResponse = NextResponse.redirect(payload.auth_url);
  redirectResponse.cookies.set({
    name: ZOHO_CONNECTION_COOKIE,
    value: payload.connection_id,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 15
  });
  return redirectResponse;
}
