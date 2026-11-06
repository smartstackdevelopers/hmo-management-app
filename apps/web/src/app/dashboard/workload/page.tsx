import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchWorkload } from "@/lib/incidentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function WorkloadPage() {
  const session = await requireAuthenticatedSession("/dashboard/workload");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["workload.read", "workload.read.own"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load workload." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const data = await fetchWorkload({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F2.4"
          title="Staff workload"
          description={`Operational workload (${data.scope}) from live caseloads, tasks, visits, handovers, and incident follow-ups.`}
        />
        <div className="flex gap-3 text-sm">
          <Link href="/dashboard/incidents" className="rounded-md border border-slate-300 px-3 py-2">
            Incidents
          </Link>
        </div>
        {data.staff.length === 0 ? (
          <EmptyState
            title="No workload rows"
            description="Workload appears when staff have active assignments or open work."
          />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {data.staff.map((row) => (
              <li key={row.staff_user_id} className="space-y-1 p-4 text-sm">
                <p className="font-mono text-xs text-slate-500">{row.staff_user_id}</p>
                <p className="text-slate-700">
                  Tenants {row.assigned_tenants} · Tasks {row.open_tasks} (overdue {row.overdue_tasks}) ·
                  Visits {row.upcoming_visits} · Handovers {row.pending_handovers} · Incident actions{" "}
                  {row.open_incident_follow_ups} (overdue {row.overdue_incident_follow_ups})
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load workload."} />
    );
  }
}
