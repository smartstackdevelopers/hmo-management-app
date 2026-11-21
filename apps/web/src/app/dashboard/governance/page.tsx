import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader, StatCard, StatGrid, StatusChip, btnSecondary } from "@/components/ui/primitives";
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
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;

  const auth = { accessToken: token, organisationId: orgId, role: session.authorization?.active_role };
  const isSuper = session.authorization?.active_role === "super_admin";

  let dash: Record<string, unknown> = {};
  try {
    dash = await fetchOrgGovernanceDashboard(auth);
  } catch {
    return (
      <ErrorState
        title="Governance unavailable"
        description="Governance isn't switched on for this organisation yet."
        retryHref="/dashboard/governance"
      />
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
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Platform"
        title="Governance"
        description="Organisation administration alongside privacy, audit and backups."
        actions={
          <>
            <Link href="/dashboard/privacy" className={btnSecondary}>
              Privacy
            </Link>
            {isSuper ? (
              <Link href="/dashboard/platform-admin" className={btnSecondary}>
                Platform admin
              </Link>
            ) : null}
          </>
        }
      />
      <StatGrid>
        {stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} />
        ))}
      </StatGrid>
      <Card>
        <CardHeader title="System health" description="Live checks from the governance dashboard." />
        <ul className="space-y-3 text-sm">
          <li className="flex items-center justify-between gap-3">
            <span className="text-slate-600">API</span>
            <StatusChip status={String(health.api_status ?? "unknown")} />
          </li>
          <li className="flex items-center justify-between gap-3">
            <span className="text-slate-600">Database</span>
            <StatusChip status={String(health.database_status ?? "unknown")} />
          </li>
          <li className="flex items-center justify-between gap-3">
            <span className="text-slate-600">Background jobs</span>
            <StatusChip status={String(health.background_jobs_status ?? "unknown")} />
          </li>
        </ul>
      </Card>
    </div>
  );
}
