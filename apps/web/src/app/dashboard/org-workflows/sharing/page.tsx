import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listSharingGrants } from "@/lib/orgWorkflowsApi";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function SecureSharingPage() {
  const session = await requireAuthenticatedSession("/dashboard/org-workflows/sharing");
  if (session.authorization && !can(session.authorization.permissions, "secure_sharing.read")) {
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
    items = (await listSharingGrants({ accessToken: token, organisationId: orgId, role: session.authorization?.active_role })).items;
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load grants"} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Secure sharing" description="Active grants only — tokens are shown once at creation." />
      {items.length === 0 ? (
        <EmptyState title="No active grants" description="Create grants via POST /api/v1/org-workflows/sharing." />
      ) : (
        <ul className="divide-y rounded-lg border bg-white">
          {items.map((g) => (
            <li key={String(g.id)} className="p-4">
              <div className="font-medium">{String(g.reference_number)}</div>
              <div className="text-sm text-slate-600">
                {String(g.resource_type)} · expires {String(g.expires_at)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
