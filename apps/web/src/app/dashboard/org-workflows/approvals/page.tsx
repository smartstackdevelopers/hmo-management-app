import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Unavailable" description="Organisation and Auth0 required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const role = session.authorization?.active_role;
  let items: Array<Record<string, unknown>> = [];
  try {
    const res = await listApprovalsInbox({ accessToken: token, organisationId: orgId, role });
    items = res.items;
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load inbox"} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Approvals inbox" description="Aggregated pending items from authorised modules." />
      {items.length === 0 ? (
        <EmptyState title="No pending approvals" description="Nothing matched your permissions and filters." />
      ) : (
        <ul className="divide-y rounded-lg border border-slate-200 bg-white">
          {items.map((item) => (
            <li key={`${item.source_type}-${item.source_id}`} className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-medium text-slate-900">{String(item.title)}</div>
                  <div className="text-sm text-slate-600">
                    {String(item.reference)} · {String(item.source_type)} · {String(item.status)}
                  </div>
                </div>
                {item.related_url_path ? (
                  <a className="text-sm text-blue-700 underline" href={String(item.related_url_path)}>
                    Open record
                  </a>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
