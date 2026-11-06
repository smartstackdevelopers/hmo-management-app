import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  fetchComplaintDashboard,
  isComplaintOverdue,
  listComplaints,
  priorityBadgeClass,
} from "@/lib/complaintsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function ComplaintsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; priority?: string; overdue?: string; q?: string }>;
}) {
  const params = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/complaints");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "complaints.manage",
      "complaints.read.own",
      "complaints.read.assigned",
      "complaints.create.own",
      "complaints.create.assigned",
      "complaints.read.property",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load complaints." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const role = session.authorization?.active_role;
    const [dashboard, page] = await Promise.all([
      fetchComplaintDashboard({ accessToken: token, organisationId: orgId, role }),
      listComplaints({
        accessToken: token,
        organisationId: orgId,
        role,
        status: params.status,
        priority: params.priority,
        overdueOnly: params.overdue === "1",
        q: params.q,
      }),
    ]);
    const canCreate = canAny(session.authorization?.permissions, [
      "complaints.manage",
      "complaints.create.own",
      "complaints.create.assigned",
    ]);
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <PageHeader
          eyebrow="Complaints"
          title="Complaints dashboard"
          description="Operational complaints workflow with priorities, deadlines, and escalations."
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Total", dashboard.total],
            ["Open", dashboard.open_count],
            ["Overdue", dashboard.overdue],
            ["Escalated", dashboard.escalated],
            ["Awaiting investigation", dashboard.awaiting_investigation],
            ["Upcoming deadlines", dashboard.upcoming_deadlines],
            ["Recently resolved", dashboard.recently_resolved],
            ["Urgent", dashboard.by_priority.urgent ?? 0],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-lg border border-slate-200 bg-white p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              <p className="text-2xl font-semibold text-slate-900">{value}</p>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {canCreate ? (
            <Link
              href="/dashboard/complaints/new"
              className="rounded bg-teal-700 px-3 py-2 text-sm text-white"
            >
              New complaint
            </Link>
          ) : null}
          <Link href="/dashboard/complaints?overdue=1" className="rounded border px-3 py-2 text-sm">
            Overdue only
          </Link>
          <Link href="/dashboard/complaints" className="rounded border px-3 py-2 text-sm">
            Clear filters
          </Link>
        </div>
        {page.items.length === 0 ? (
          <EmptyState title="No complaints" description="No complaints match the current filters." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((row) => (
              <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div>
                  <Link
                    href={`/dashboard/complaints/${row.id}`}
                    className="font-medium text-teal-900 hover:underline"
                  >
                    {row.reference_number} · {row.title}
                  </Link>
                  <p className="text-sm text-slate-600">
                    {row.status.replaceAll("_", " ")}
                    {isComplaintOverdue(row) ? " · overdue" : ""}
                    {row.open_escalation ? " · escalation open" : ""}
                  </p>
                </div>
                <span
                  className={`rounded border px-2 py-0.5 text-xs uppercase ${priorityBadgeClass(row.priority)}`}
                >
                  {row.priority}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load complaints."}
      />
    );
  }
}
