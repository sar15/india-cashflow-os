import { NextRequest, NextResponse } from "next/server";

import { getApiTokenForSession, getSessionFromRequest } from "@/lib/auth";
import { getApiBaseUrl, getApiRequestHeaders } from "@/lib/api";

const ZOHO_CONNECTION_COOKIE = "cashflow_zoho_connection_id";

function redirectWithStatus(request: NextRequest, status: string, importBatchId?: string) {
  const destination = new URL(importBatchId ? "/setup" : "/imports", request.url);
  destination.searchParams.set("zoho", status);
  if (importBatchId) {
    destination.searchParams.set("importBatchId", importBatchId);
  }

  const response = NextResponse.redirect(destination);
  response.cookies.set({
    name: ZOHO_CONNECTION_COOKIE,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date(0)
  });
  return response;
}

export async function GET(request: NextRequest) {
  const session = getSessionFromRequest(request);
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const apiToken = getApiTokenForSession(session);
  const apiBase = getApiBaseUrl();
  if (!apiToken || !apiBase) {
    return redirectWithStatus(request, "unavailable");
  }

  const connectionId = request.cookies.get(ZOHO_CONNECTION_COOKIE)?.value;
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const accountsServer = request.nextUrl.searchParams.get("accounts-server");
  const error = request.nextUrl.searchParams.get("error");

  if (error) {
    return redirectWithStatus(request, "denied");
  }
  if (!connectionId || !code || !state) {
    return redirectWithStatus(request, "invalid_callback");
  }

  const exchangeResponse = await fetch(`${apiBase}/v1/sources/zoho/exchange`, {
    method: "POST",
    cache: "no-store",
    headers: getApiRequestHeaders(
      {
        "content-type": "application/json"
      },
      apiToken
    ),
    body: JSON.stringify({
      connection_id: connectionId,
      code,
      state,
      accounts_server: accountsServer ?? undefined
    })
  });

  if (!exchangeResponse.ok) {
    return redirectWithStatus(request, "exchange_failed");
  }

  const syncResponse = await fetch(`${apiBase}/v1/sources/zoho/${encodeURIComponent(connectionId)}/sync`, {
    method: "POST",
    cache: "no-store",
    headers: getApiRequestHeaders(undefined, apiToken)
  });

  if (!syncResponse.ok) {
    return redirectWithStatus(request, "sync_failed");
  }

  const syncPayload = (await syncResponse.json()) as {
    import_batch?: {
      import_batch_id?: string;
    };
  };
  const importBatchId = syncPayload.import_batch?.import_batch_id;
  return redirectWithStatus(request, "connected", importBatchId);
}
