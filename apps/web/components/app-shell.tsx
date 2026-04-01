import type { ReactNode } from "react";
import Link from "next/link";

import { requireCurrentSession } from "@/lib/auth";

const NAVIGATION = [
  { href: "/", label: "Overview" },
  { href: "/imports", label: "Connect or Upload" },
  { href: "/setup", label: "Cash Rules" },
  { href: "/dashboard", label: "Forecast Dashboard" }
];

export async function AppShell({
  children,
  activePath
}: Readonly<{ children: ReactNode; activePath: string }>) {
  const session = await requireCurrentSession();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">CF</div>
          <div>
            <div className="brand-title">India Cashflow OS</div>
            <div className="sidebar-copy">
              Short-horizon liquidity visibility for Indian SMEs, finance teams, and CA-assisted workflows.
            </div>
          </div>
        </div>
        <nav className="nav-list">
          {NAVIGATION.map((item) => (
            <Link key={item.href} href={item.href} className={`nav-link ${activePath === item.href ? "active" : ""}`}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="session-card">
          <div className="kpi-label">Signed in as</div>
          <strong>{session.name}</strong>
          <div className="kpi-description">
            {session.role.replace(/_/g, " ")} · {session.orgId}
          </div>
          <form action="/api/auth/logout" method="post">
            <button className="button secondary session-logout" type="submit">
              Sign Out
            </button>
          </form>
        </div>
      </aside>
      <main className="shell-content">{children}</main>
    </div>
  );
}
