import { AppShell } from "@/components/app-shell";
import { SetupWorkbench } from "@/components/setup-workbench";

export default async function SetupPage({
  searchParams
}: Readonly<{ searchParams?: Promise<{ importBatchId?: string }> }>) {
  const params = searchParams ? await searchParams : undefined;

  return (
    <AppShell activePath="/setup">
      <section className="hero-card">
        <span className="eyebrow">Step 2 · Review Exceptions</span>
        <h1 className="page-title">Fix missing dates and critical issues.</h1>
        <p>
          We parse your import deterministically. If any data is incomplete or corrupted, resolve it here 
          before we generate the forecast. Clean data ensures accurate results.
        </p>
      </section>

      <section className="one-column">
        <SetupWorkbench initialImportBatchId={params?.importBatchId} />
      </section>
    </AppShell>
  );
}
