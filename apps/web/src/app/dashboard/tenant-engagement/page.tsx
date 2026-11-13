import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { getEngagementReports, getTenantEngagementDashboard } from "@/lib/tenantEngagementApi";

const READ = ["tenant_engagement.read", "tenant_engagement.tenant", "tenant_engagement.manage", "tenant_engagement.staff"];

export default async function TenantEngagementPage() {
  const session = await requireAuthenticatedSession("/dashboard/tenant-engagement");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  const perms = session.authorization?.permissions ?? [];
  const admin = perms.includes("tenant_engagement.manage") || perms.includes("tenant_engagement.reports");
  const tenant = perms.includes("tenant_engagement.tenant");

  let stats: Record<string, unknown> = {};
  let dash: Record<string, unknown> = {};

  try {
    if (admin) stats = await getEngagementReports(token, orgId);
    if (tenant) dash = await getTenantEngagementDashboard(token, orgId);
  } catch {
    return (
      <ErrorState description="Tenant Engagement is disabled until TENANT_ENGAGEMENT_GLOBAL_ENABLED and organisation settings are approved." />
    );
  }

  const goals = (dash.goals ?? []) as Record<string, unknown>[];
  const timeline = (dash.timeline ?? []) as Record<string, unknown>[];

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Tenant Engagement (add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Voluntary personal development — points and badges do not affect housing or essential services.
        </p>
      </header>
      {admin ? (
        <section className="grid gap-4 sm:grid-cols-4">
          <Stat label="Active goals" value={String(stats.active_goals ?? "0")} />
          <Stat label="Completed goals" value={String(stats.completed_goals ?? "0")} />
          <Stat label="Badges" value={String(stats.badges_awarded ?? "0")} />
          <Stat label="Activities" value={String(stats.activities_completed ?? "0")} />
        </section>
      ) : null}
      {tenant ? (
        <>
          <section className="grid gap-4 sm:grid-cols-3">
            <Stat label="Points" value={String(dash.points_total ?? "0")} />
            <Stat label="Badges" value={String(dash.badges_count ?? "0")} />
            <Stat label="LMS enrollments" value={String(dash.lms_enrollments ?? "0")} />
          </section>
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="font-medium text-slate-800">My goals</h2>
            <ul className="mt-3 divide-y divide-slate-100 text-sm">
              {goals.length === 0 ? (
                <li className="py-2 text-slate-500">No goals yet.</li>
              ) : (
                goals.map((g) => (
                  <li key={String(g.id)} className="flex justify-between py-2">
                    <span>{String(g.title)}</span>
                    <span className="text-slate-500">
                      {String(g.completion_percent)}% — {String(g.progress_status)}
                    </span>
                  </li>
                ))
              )}
            </ul>
          </section>
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="font-medium text-slate-800">Progress timeline</h2>
            <ul className="mt-3 divide-y divide-slate-100 text-sm">
              {timeline.length === 0 ? (
                <li className="py-2 text-slate-500">No events yet.</li>
              ) : (
                timeline.map((t, i) => (
                  <li key={i} className="py-2">
                    {String(t.summary)}
                  </li>
                ))
              )}
            </ul>
          </section>
        </>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}
