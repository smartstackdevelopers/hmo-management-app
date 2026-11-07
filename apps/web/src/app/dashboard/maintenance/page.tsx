import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchMaintenanceDashboard, isEmergencyRequest, listMaintenanceRequests, maintenancePriorityBadgeClass } from "@/lib/maintenanceApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function MaintenanceListPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; priority?: string; q?: string; pending?: string }>;
}) {
  const params = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/maintenance");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "maintenance.manage",
      "maintenance.read.own",
      "maintenance.read.assigned",
      "maintenance.create.own",
      "maintenance.create.assigned",
      "maintenance.read.property",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load maintenance." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const role = session.authorization?.active_role;
    const [dashboard, page] = await Promise.all([
      fetchMaintenanceDashboard({ accessToken: token, organisationId: orgId, role }),
      listMaintenanceRequests({
        accessToken: token,
        organisationId: orgId,
        role,
        status: params.status,
        priority: params.priority,
        pendingApproval: params.pending === "1",
        q: params.q,
      }),
    ]);
    const canCreate = canAny(session.authorization?.permissions, [
      "maintenance.manage",
      "maintenance.create.own",
      "maintenance.create.assigned",
    ]);
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <PageHeader
          eyebrow="Maintenance"
          title="Maintenance dashboard"
          description="Requests, visits, approvals, and emergency guidance for gas- and fire-related categories."
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Total", dashboard.total],
            ["Open", dashboard.open_count],
            ["Awaiting approval", dashboard.awaiting_approval],
            ["Scheduled visits", dashboard.scheduled_visits],
            ["In progress", dashboard.in_progress],
            ["Overdue / delayed (visit)", dashboard.overdue_scheduled],
            ["Urgent + emergency", dashboard.urgent_and_emergency],
            ["Emergency priority", dashboard.emergency],
            ["Recently completed (7d)", dashboard.recently_completed],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-lg border border-slate-200 bg-white p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              <p className="text-2xl font-semibold text-slate-900">{value}</p>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {canCreate ? (
            <Link href="/dashboard/maintenance/new" className="rounded bg-teal-700 px-3 py-2 text-sm text-white">
              New request
            </Link>
          ) : null}
          <Link href="/dashboard/maintenance?pending=1" className="rounded border px-3 py-2 text-sm">
            Pending approvals
          </Link>
          <Link href="/dashboard/maintenance" className="rounded border px-3 py-2 text-sm">
            Clear filters
          </Link>
        </div>
        {page.items.length === 0 ? (
          <EmptyState title="No requests" description="No maintenance requests match the current filters." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((row) => (
              <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div>
                  <Link
                    href={`/dashboard/maintenance/${row.id}`}
                    className="font-medium text-teal-900 hover:underline"
                  >
                    {row.reference_number} · {row.title}
                  </Link>
                  <p className="text-sm text-slate-600">{row.status.replaceAll("_", " ")}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {isEmergencyRequest(row) ? (
                    <span className="rounded border border-red-500 bg-red-50 px-2 py-0.5 text-xs font-semibold uppercase text-red-950">
                      Emergency
                    </span>
                  ) : null}
                  <span
                    className={`rounded border px-2 py-0.5 text-xs uppercase ${maintenancePriorityBadgeClass(row.priority)}`}
                  >
                    {row.priority}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load maintenance."}
      />
    );
  }
}
