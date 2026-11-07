import { redirect } from "next/navigation";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listMaintenanceRequests, maintenancePriorityBadgeClass } from "@/lib/maintenanceApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function MaintenancePendingPage() {
  const session = await requireAuthenticatedSession("/dashboard/maintenance/pending");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["maintenance.manage", "maintenance.approve"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load approvals." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const role = session.authorization?.active_role;
    const page = await listMaintenanceRequests({
      accessToken: token,
      organisationId: orgId,
      role,
      pendingApproval: true,
    });
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader eyebrow="Maintenance" title="Pending approvals" description="Requests awaiting organiser approval." />
        {page.items.length === 0 ? (
          <EmptyState title="None pending" description="No maintenance requests are awaiting approval." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((row) => (
              <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div>
                  <Link href={`/dashboard/maintenance/${row.id}`} className="font-medium text-teal-900 hover:underline">
                    {row.reference_number} · {row.title}
                  </Link>
                  <p className="text-sm text-slate-600">{row.status.replaceAll("_", " ")}</p>
                </div>
                <span className={`rounded border px-2 py-0.5 text-xs uppercase ${maintenancePriorityBadgeClass(row.priority)}`}>
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
      <ErrorState description={error instanceof Error ? error.message : "Failed to load pending approvals."} />
    );
  }
}
