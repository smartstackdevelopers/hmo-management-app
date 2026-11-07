import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Unavailable" description="Organisation and Auth0 required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  let items: Array<Record<string, unknown>> = [];
  try {
    items = (await listWorkflows({ accessToken: token, organisationId: orgId, role: session.authorization?.active_role })).items;
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load workflows"} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Approval workflows" description="Versioned configuration — use API to create and activate." />
      {items.length === 0 ? (
        <EmptyState title="No workflows" description="Create workflows via POST /api/v1/org-workflows/workflows." />
      ) : (
        <ul className="divide-y rounded-lg border bg-white">
          {items.map((w) => (
            <li key={String(w.id)} className="p-4">
              <div className="font-medium">{String(w.name)}</div>
              <div className="text-sm text-slate-600">
                {String(w.code)} · {String(w.process_type)} · {String(w.status)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
