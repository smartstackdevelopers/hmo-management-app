import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th, linkClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listApprovalsInbox } from "@/lib/orgWorkflowsApi";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function ApprovalsInboxPage() {
  const session = await requireAuthenticatedSession("/dashboard/org-workflows/approvals");
  if (session.authorization && !can(session.authorization.permissions, "approvals.inbox.read")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Select the organisation you're working in." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  const role = session.authorization?.active_role;
  let items: Array<Record<string, unknown>> = [];
  try {
    const res = await listApprovalsInbox({ accessToken: token, organisationId: orgId, role });
    items = res.items;
  } catch {
    return <ErrorState description={"Failed to load inbox"} />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Approvals inbox"
        description="Pending items from the modules you can review."
      />
      {items.length === 0 ? (
        <EmptyState title="No pending approvals" description="Requests waiting for you will appear here." />
      ) : (
        <DataTable caption="Approvals inbox">
          <thead>
            <tr>
              <Th>Request</Th>
              <Th>Reference</Th>
              <Th>Source</Th>
              <Th>Status</Th>
              <Th>Record</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={`${item.source_type}-${item.source_id}`}>
                <Td className="font-semibold text-slate-900">{String(item.title)}</Td>
                <Td>{String(item.reference)}</Td>
                <Td>{String(item.source_type)}</Td>
                <Td>
                  <StatusChip status={String(item.status)} />
                </Td>
                <Td>
                  {item.related_url_path ? (
                    <a className={linkClass} href={String(item.related_url_path)}>
                      Open record
                    </a>
                  ) : (
                    "—"
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">Showing {items.length === 0 ? "0" : `1–${items.length}`} of {items.length}</p>
    </div>
  );
}
