import { getApiTokenForSession, requireCurrentSession } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";
import { DashboardExperience } from "@/components/dashboard-experience";
import { getDashboardData } from "@/lib/demo-data";

export default async function DashboardPage({
  searchParams
}: Readonly<{ searchParams?: Promise<{ forecastRunId?: string }> }>) {
  const params = searchParams ? await searchParams : undefined;
  const session = await requireCurrentSession();
  const dashboard = await getDashboardData(params?.forecastRunId, getApiTokenForSession(session));

  return (
    <AppShell activePath="/dashboard">
      <DashboardExperience dashboard={dashboard} />
    </AppShell>
  );
}
