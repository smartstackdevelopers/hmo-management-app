import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listAuditEvents } from "@/lib/orgWorkflowsApi";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DashboardAuditPage() {
  const session = await requireAuthenticatedSession("/dashboard/audit");
  if (session.authorization && !can(session.authorization.permissions, "audit_logs.read")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Select an organisation to view audit logs." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load audit logs." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }
  let items: Array<Record<string, unknown>> = [];
  let total = 0;
  try {
    const res = await listAuditEvents({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    items = res.items;
    total = res.total;
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load audit events"} />;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Audit logs"
        description="Read-only view of organisation audit events (F1.7). Listing is audited by the API."
      />
      <p className="text-sm text-slate-600">Total events: {total}. This UI is read-only.</p>
      {items.length === 0 ? (
        <EmptyState title="No events" description="No audit records matched this page." />
      ) : (
        <ul className="divide-y rounded-lg border border-slate-200 bg-white text-sm">
          {items.map((ev) => (
            <li key={String(ev.id)} className="p-4">
              <div className="font-medium text-slate-900">{String(ev.action)}</div>
              <div className="text-slate-600">
                {String(ev.resource_type)} · {String(ev.created_at)} · {String(ev.summary ?? "")}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
