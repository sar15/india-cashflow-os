import { NextRequest, NextResponse } from "next/server";

import { getApiBaseUrl } from "@/lib/api";

export async function GET(_request: NextRequest) {
  const apiBase = getApiBaseUrl();
  if (!apiBase) {
    return NextResponse.json(
      { error: "API not configured." },
      { status: 503 }
    );
  }

  const upstream = await fetch(`${apiBase}/v1/templates/cashflow-os-template.xlsx`, {
    cache: "no-store",
  });

  if (!upstream.ok) {
    return NextResponse.json(
      { error: "Template generation failed." },
      { status: upstream.status }
    );
  }

  const buffer = await upstream.arrayBuffer();
  return new NextResponse(buffer, {
    status: 200,
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition": 'attachment; filename="cashflow-os-template.xlsx"',
    },
  });
}
