import { redirect } from "next/navigation";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { PriorityChip } from "@/components/maintenance/PriorityChip";
import { DataTable, StatusChip, Td, Th, btnSecondary } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listMaintenanceRequests } from "@/lib/maintenanceApi";
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
    return <EmptyState title="Choose an organisation" description="Select an organisation to see repairs awaiting approval." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in unavailable" description="We can't load approvals right now. Please try again later." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState title="Session expired" description="Please sign in again to see approvals." />;
    const role = session.authorization?.active_role;
    const page = await listMaintenanceRequests({
      accessToken: token,
      organisationId: orgId,
      role,
      pendingApproval: true,
    });
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <PageHeader
          eyebrow="Maintenance"
          title="Pending approvals"
          description="Repairs waiting for your approval before work can go ahead."
          actions={
            <Link href="/dashboard/maintenance" className={btnSecondary}>
              All repairs
            </Link>
          }
        />
        {page.items.length === 0 ? (
          <EmptyState
            title="Nothing waiting"
            description="No repairs are awaiting approval right now."
            action={{ label: "Back to repairs", href: "/dashboard/maintenance" }}
          />
        ) : (
          <DataTable caption="Repairs awaiting approval">
            <thead>
              <tr>
                <Th>Repair</Th>
                <Th>Reference</Th>
                <Th>Priority</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50">
                  <Td>
                    <Link href={`/dashboard/maintenance/${row.id}`} className="font-semibold text-slate-900 hover:text-brand-700 hover:underline">
                      {row.title}
                    </Link>
                  </Td>
                  <Td className="text-slate-500">{row.reference_number}</Td>
                  <Td>
                    <PriorityChip priority={row.priority} />
                  </Td>
                  <Td>
                    <StatusChip status={row.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "We couldn't load pending approvals."}
        retryHref="/dashboard/maintenance/pending"
      />
    );
  }
}
