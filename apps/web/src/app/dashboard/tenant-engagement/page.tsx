import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader, DataTable, StatCard, StatGrid, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { getEngagementReports, getTenantEngagementDashboard } from "@/lib/tenantEngagementApi";

const READ = ["tenant_engagement.read", "tenant_engagement.tenant", "tenant_engagement.manage", "tenant_engagement.staff"];

function text(value: unknown): string {
  return value == null || value === "" ? "—" : String(value);
}

export default async function TenantEngagementPage() {
  const session = await requireAuthenticatedSession("/dashboard/tenant-engagement");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/tenant-engagement" />;

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
      <ErrorState description="Tenant engagement stays off until the organisation turns the add-on on." retryHref="/dashboard/tenant-engagement" />
    );
  }

  const goals = (dash.goals ?? []) as Record<string, unknown>[];
  const timeline = (dash.timeline ?? []) as Record<string, unknown>[];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Community"
        title="Tenant engagement"
        description="Voluntary personal development. Points and badges do not affect housing or essential services."
      />
      {admin ? (
        <StatGrid>
          <StatCard label="Active goals" value={text(stats.active_goals ?? 0)} tone="blue" />
          <StatCard label="Completed goals" value={text(stats.completed_goals ?? 0)} tone="green" />
          <StatCard label="Badges" value={text(stats.badges_awarded ?? 0)} />
          <StatCard label="Activities" value={text(stats.activities_completed ?? 0)} />
        </StatGrid>
      ) : null}
      {tenant ? (
        <>
          <StatGrid>
            <StatCard label="Points" value={text(dash.points_total ?? 0)} />
            <StatCard label="Badges" value={text(dash.badges_count ?? 0)} />
            <StatCard label="Learning enrolments" value={text(dash.lms_enrollments ?? 0)} />
          </StatGrid>
          {goals.length === 0 ? (
            <EmptyState title="No goals yet" description="Goals you start will appear here." />
          ) : (
            <DataTable caption="My goals">
              <thead>
                <tr>
                  <Th>Goal</Th>
                  <Th>Progress</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {goals.map((goal) => (
                  <tr key={text(goal.id)} className="hover:bg-slate-50/60">
                    <Td className="font-semibold text-slate-900">{text(goal.title)}</Td>
                    <Td className="tabular-nums">{text(goal.completion_percent)}%</Td>
                    <Td>
                      <StatusChip status={text(goal.progress_status)} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
          <Card>
            <CardHeader title="Progress timeline" />
            {timeline.length === 0 ? (
              <p className="text-sm text-slate-500">No events yet.</p>
            ) : (
              <ul className="divide-y divide-slate-100 text-sm">
                {timeline.map((event, index) => (
                  <li key={`${text(event.summary)}-${index}`} className="py-2.5 text-slate-700">
                    {text(event.summary)}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      ) : null}
      {!admin && !tenant ? (
        <EmptyState title="Nothing to show yet" description="Engagement figures appear when your role can see them." />
      ) : null}
    </div>
  );
}
