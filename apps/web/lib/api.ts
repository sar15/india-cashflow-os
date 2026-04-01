export function getApiBaseUrl() {
  const apiBase =
    process.env.API_URL ??
    process.env.API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "https://cashflow-os-api.onrender.com";
    
  if (apiBase) return apiBase.replace(/\/$/, "");

  // Fallback for Vercel Server Components
  const vercelUrl = process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL;
  if (vercelUrl) {
    return `https://${vercelUrl}/backend`;
  }

  return "https://cashflow-os-api.onrender.com";
}

export function getApiAuthToken() {
  return process.env.API_AUTH_TOKEN ?? process.env.CASHFLOW_API_TOKEN ?? "demo-owner-token";
}

export function getApiRequestHeaders(extraHeaders?: HeadersInit, token?: string | null) {
  return {
    Authorization: `Bearer ${token ?? getApiAuthToken()}`,
    ...(extraHeaders ?? {})
  };
}
