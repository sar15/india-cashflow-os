import { NextRequest, NextResponse } from "next/server";

import { getApiTokenForSession, getSessionFromRequest } from "@/lib/auth";
import { getApiBaseUrl, getApiRequestHeaders } from "@/lib/api";

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
      { error: "Set API_BASE_URL or NEXT_PUBLIC_API_BASE_URL to enable imports." },
      { status: 503 }
    );
  }

  const formData = await request.formData();
  const orgId = session.orgId;
  const sourceType = String(formData.get("sourceType") ?? "manual");
  const sourceHint = String(formData.get("sourceHint") ?? "");
  const useDemo = String(formData.get("useDemo") ?? "false") === "true";
  const file = formData.get("file");

  let upstreamResponse: Response;
  if (useDemo) {
    upstreamResponse = await fetch(`${apiBase}/v1/imports`, {
      method: "POST",
      headers: getApiRequestHeaders(
        {
        "content-type": "application/json"
        },
        apiToken
      ),
      body: JSON.stringify({
        org_id: orgId,
        source_type: sourceType,
        filename: "demo-upload.xlsx",
        source_hint: sourceHint || undefined,
        use_demo: true
      }),
      cache: "no-store"
    });
  } else {
    if (!(file instanceof File)) {
      return NextResponse.json({ error: "Choose a file before uploading." }, { status: 400 });
    }
    const upstreamForm = new FormData();
    upstreamForm.set("org_id", orgId);
    upstreamForm.set("source_type", sourceType);
    if (sourceHint) {
      upstreamForm.set("source_hint", sourceHint);
    }
    upstreamForm.set("file", file, file.name);

    upstreamResponse = await fetch(`${apiBase}/v1/imports`, {
      method: "POST",
      headers: getApiRequestHeaders(undefined, apiToken),
      body: upstreamForm,
      cache: "no-store"
    });
  }

  const payload = await upstreamResponse.json();
  if (!upstreamResponse.ok) {
    return NextResponse.json(payload, { status: upstreamResponse.status });
  }
  return NextResponse.json(payload);
}
