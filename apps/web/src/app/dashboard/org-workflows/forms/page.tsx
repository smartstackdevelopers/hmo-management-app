import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listCustomForms } from "@/lib/orgWorkflowsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const ANY = ["organisation.forms.manage", "organisation.forms.submit"];

export default async function CustomFormsPage() {
  const session = await requireAuthenticatedSession("/dashboard/org-workflows/forms");
  if (session.authorization && !canAny(session.authorization.permissions, ANY)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation and Auth0 required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const manage = session.authorization?.permissions.includes("organisation.forms.manage");
  let items: Array<Record<string, unknown>> = [];
  try {
    items = (
      await listCustomForms({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization?.active_role,
        publishedOnly: !manage,
      })
    ).items;
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load forms"} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Custom forms" description="Organisation-scoped forms with versioned schemas." />
      {items.length === 0 ? (
        <EmptyState title="No forms" description="Publish forms via the API or add draft forms as an admin." />
      ) : (
        <ul className="divide-y rounded-lg border bg-white">
          {items.map((f) => (
            <li key={String(f.id)} className="p-4">
              <div className="font-medium">{String(f.title)}</div>
              <div className="text-sm text-slate-600">
                {String(f.code)} · {String(f.status)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
