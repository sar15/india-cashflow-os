import { NextRequest, NextResponse } from "next/server";

import { authenticateUser, buildSessionCookie } from "@/lib/auth";

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as { email?: string; password?: string };
  const session = authenticateUser(String(payload.email ?? ""), String(payload.password ?? ""));
  if (!session) {
    return NextResponse.json({ error: "Invalid email or password." }, { status: 401 });
  }

  const response = NextResponse.json({
    user: {
      email: session.email,
      name: session.name,
      orgId: session.orgId,
      role: session.role
    }
  });
  response.cookies.set(buildSessionCookie(session));
  return response;
}
