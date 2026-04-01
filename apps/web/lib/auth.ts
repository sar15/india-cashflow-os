import "server-only";

import { createHmac, pbkdf2Sync, randomBytes, timingSafeEqual } from "crypto";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";

const SESSION_COOKIE_NAME = "cashflow_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7;

type ConfiguredWebUser = {
  email: string;
  name: string;
  orgId: string;
  role: string;
  apiToken: string;
  passwordHash?: string;
  password?: string;
};

type SessionPayload = {
  email: string;
  name: string;
  orgId: string;
  role: string;
  exp: number;
};

export type WebSession = {
  email: string;
  name: string;
  orgId: string;
  role: string;
  expiresAt: number;
};

function getSessionSecret() {
  return process.env.CASHFLOW_SESSION_SECRET ?? "cashflow-dev-session-secret";
}

function toBase64Url(value: Buffer | string) {
  return Buffer.from(value)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function fromBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4));
  return Buffer.from(`${normalized}${padding}`, "base64");
}

function signPayload(payload: string) {
  return toBase64Url(createHmac("sha256", getSessionSecret()).update(payload).digest());
}

function getDefaultUsers(): ConfiguredWebUser[] {
  return [
    {
      email: "owner@demo.local",
      name: "Demo Owner",
      orgId: "demo-org",
      role: "owner",
      apiToken: "demo-owner-token",
      password: "demo-owner"
    },
    {
      email: "finance@demo.local",
      name: "Demo Finance Manager",
      orgId: "demo-org",
      role: "finance_manager",
      apiToken: "demo-finance-token",
      password: "demo-finance"
    },
    {
      email: "accountant@demo.local",
      name: "Demo Accountant",
      orgId: "demo-org",
      role: "accountant",
      apiToken: "demo-accountant-token",
      password: "demo-accountant"
    },
    {
      email: "viewer@demo.local",
      name: "Demo Viewer",
      orgId: "demo-org",
      role: "viewer",
      apiToken: "demo-viewer-token",
      password: "demo-viewer"
    }
  ];
}

function parseConfiguredUsers(): ConfiguredWebUser[] {
  const rawUsers = process.env.CASHFLOW_WEB_USERS_JSON;
  if (!rawUsers) {
    if (process.env.CASHFLOW_DISABLE_DEMO_USERS === "1") {
      return [];
    }
    return getDefaultUsers();
  }

  const payload = JSON.parse(rawUsers);
  if (!Array.isArray(payload)) {
    throw new Error("CASHFLOW_WEB_USERS_JSON must be a JSON array.");
  }

  return payload.map((entry) => {
    const user = entry as Partial<ConfiguredWebUser>;
    if (!user.email || !user.name || !user.orgId || !user.role || !user.apiToken) {
      throw new Error("Each CASHFLOW_WEB_USERS_JSON entry requires email, name, orgId, role, and apiToken.");
    }
    if (!user.passwordHash && !user.password) {
      throw new Error("Each CASHFLOW_WEB_USERS_JSON entry requires passwordHash or password.");
    }
    return {
      email: user.email.toLowerCase(),
      name: user.name,
      orgId: user.orgId,
      role: user.role,
      apiToken: user.apiToken,
      passwordHash: user.passwordHash,
      password: user.password
    };
  });
}

function getUserByEmail(email: string) {
  const normalizedEmail = email.trim().toLowerCase();
  return parseConfiguredUsers().find((user) => user.email === normalizedEmail) ?? null;
}

function verifyPasswordHash(password: string, encodedHash: string) {
  const [scheme, digest, iterationsValue, saltValue, hashValue] = encodedHash.split("$");
  if (scheme !== "pbkdf2" || !digest || !iterationsValue || !saltValue || !hashValue) {
    return false;
  }

  const iterations = Number(iterationsValue);
  if (!Number.isFinite(iterations) || iterations <= 0) {
    return false;
  }

  const salt = fromBase64Url(saltValue);
  const expectedHash = fromBase64Url(hashValue);
  const derived = pbkdf2Sync(password, salt, iterations, expectedHash.length, digest);
  return timingSafeEqual(derived, expectedHash);
}

function verifyPassword(password: string, user: ConfiguredWebUser) {
  if (user.passwordHash) {
    return verifyPasswordHash(password, user.passwordHash);
  }
  if (typeof user.password === "string") {
    return password === user.password;
  }
  return false;
}

function encodeSession(session: WebSession) {
  const payload = JSON.stringify({
    email: session.email,
    name: session.name,
    orgId: session.orgId,
    role: session.role,
    exp: session.expiresAt
  } satisfies SessionPayload);
  const encodedPayload = toBase64Url(payload);
  const signature = signPayload(encodedPayload);
  return `${encodedPayload}.${signature}`;
}

function decodeSessionCookie(value: string | undefined | null): WebSession | null {
  if (!value) {
    return null;
  }

  const [encodedPayload, encodedSignature] = value.split(".");
  if (!encodedPayload || !encodedSignature) {
    return null;
  }

  const expectedSignature = signPayload(encodedPayload);
  if (
    encodedSignature.length !== expectedSignature.length ||
    !timingSafeEqual(Buffer.from(encodedSignature), Buffer.from(expectedSignature))
  ) {
    return null;
  }

  try {
    const payload = JSON.parse(fromBase64Url(encodedPayload).toString("utf-8")) as SessionPayload;
    if (payload.exp <= Date.now()) {
      return null;
    }
    return {
      email: payload.email,
      name: payload.name,
      orgId: payload.orgId,
      role: payload.role,
      expiresAt: payload.exp
    };
  } catch {
    return null;
  }
}

export function createPasswordHash(password: string) {
  const iterations = 600000;
  const salt = randomBytes(16);
  const hash = pbkdf2Sync(password, salt, iterations, 32, "sha256");
  return `pbkdf2$sha256$${iterations}$${toBase64Url(salt)}$${toBase64Url(hash)}`;
}

export function authenticateUser(email: string, password: string): WebSession | null {
  const user = getUserByEmail(email);
  if (!user || !verifyPassword(password, user)) {
    return null;
  }

  return {
    email: user.email,
    name: user.name,
    orgId: user.orgId,
    role: user.role,
    expiresAt: Date.now() + SESSION_TTL_SECONDS * 1000
  };
}

export function getApiTokenForSession(session: WebSession) {
  return getUserByEmail(session.email)?.apiToken ?? null;
}

export function buildSessionCookie(session: WebSession) {
  return {
    name: SESSION_COOKIE_NAME,
    value: encodeSession(session),
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date(session.expiresAt)
  };
}

export function buildLogoutCookie() {
  return {
    name: SESSION_COOKIE_NAME,
    value: "",
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date(0)
  };
}

export async function getCurrentSession() {
  const cookieStore = await cookies();
  return decodeSessionCookie(cookieStore.get(SESSION_COOKIE_NAME)?.value);
}

export async function requireCurrentSession() {
  const session = await getCurrentSession();
  if (!session) {
    redirect("/login");
  }
  return session;
}

export function getSessionFromRequest(request: NextRequest) {
  return decodeSessionCookie(request.cookies.get(SESSION_COOKIE_NAME)?.value);
}
