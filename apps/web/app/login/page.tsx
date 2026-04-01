import { redirect } from "next/navigation";

import { LoginForm } from "@/components/login-form";
import { getCurrentSession } from "@/lib/auth";

export default async function LoginPage() {
  const session = await getCurrentSession();
  if (session) {
    redirect("/");
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <span className="eyebrow">Secure Workspace Access</span>
        <h1 className="page-title">Sign in to the cash cockpit.</h1>
        <p className="kpi-description">
          The deployed app uses signed web sessions so the product UI is no longer exposed behind demo credentials.
        </p>
        <LoginForm />
      </section>
    </main>
  );
}
