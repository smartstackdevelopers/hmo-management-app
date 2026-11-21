import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th, humanize } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listWorkflows } from "@/lib/orgWorkflowsApi";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function WorkflowsConfigPage() {
  const session = await requireAuthenticatedSession("/dashboard/org-workflows/workflows");
  if (session.authorization && !can(session.authorization.permissions, "organisation.workflows.manage")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Select the organisation you're working in." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  let items: Array<Record<string, unknown>> = [];
  try {
    items = (await listWorkflows({ accessToken: token, organisationId: orgId, role: session.authorization?.active_role })).items;
  } catch {
    return <ErrorState description={"Failed to load workflows"} />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader eyebrow="Operations" title="Approval workflows" description="Versioned approval workflows for this organisation." />
      {items.length === 0 ? (
        <EmptyState title="No workflows" description="Workflows you configure will appear here." />
      ) : (
        <DataTable caption="Approval workflows">
          <thead>
            <tr>
              <Th>Workflow</Th>
              <Th>Process</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((w) => (
              <tr key={String(w.id)}>
                <Td className="font-semibold text-slate-900">{String(w.name)}</Td>
                <Td>{humanize(String(w.process_type ?? ""))}</Td>
                <Td>
                  <StatusChip status={String(w.status)} />
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
