import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchOrgGovernanceDashboard } from "@/lib/platformGovernanceApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = ["platform_governance.read", "platform_governance.manage", "platform_governance.compliance"];

export default async function GovernancePage() {
  const session = await requireAuthenticatedSession("/dashboard/governance");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  const auth = { accessToken: token, organisationId: orgId, role: session.authorization?.active_role };
  const isSuper = session.authorization?.active_role === "super_admin";

  let dash: Record<string, unknown> = {};
  try {
    dash = await fetchOrgGovernanceDashboard(auth);
  } catch {
    return (
      <ErrorState description="Governance is disabled until PLATFORM_GOVERNANCE_GLOBAL_ENABLED and organisation governance settings are enabled." />
    );
  }

  const stats = [
    { label: "Compliance policies", value: String(dash.compliance_policies ?? "0") },
    { label: "Open compliance tasks", value: String(dash.open_compliance_tasks ?? "0") },
    { label: "Privacy requests pending", value: String(dash.pending_privacy_requests ?? "0") },
    { label: "Open incidents", value: String(dash.open_incidents ?? "0") },
  ];

  const health = (dash.system_health ?? {}) as Record<string, unknown>;

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="flex flex-wrap justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Governance &amp; compliance (F8.12)</h1>
          <p className="mt-1 text-sm text-slate-600">Organisation administration — complements privacy, audit and backups.</p>
        </div>
        <div className="flex gap-2 text-sm">
          <Link href="/dashboard/privacy" className="rounded border border-slate-200 bg-white px-3 py-1.5 hover:bg-slate-50">
            Privacy (F7.2)
          </Link>
          {isSuper ? (
            <Link href="/dashboard/platform-admin" className="rounded border border-slate-200 bg-white px-3 py-1.5 hover:bg-slate-50">
              Platform admin
            </Link>
          ) : null}
        </div>
      </header>
      <section className="grid gap-3 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs uppercase tracking-wide text-slate-500">{s.label}</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{s.value}</div>
          </div>
        ))}
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <h2 className="font-medium text-slate-800">System health (live checks)</h2>
        <ul className="mt-2 space-y-1 text-slate-600">
          <li>API: {String(health.api_status ?? "unknown")}</li>
          <li>Database: {String(health.database_status ?? "unknown")}</li>
          <li>Background jobs: {String(health.background_jobs_status ?? "unknown")}</li>
        </ul>
      </section>
    </div>
  );
}
