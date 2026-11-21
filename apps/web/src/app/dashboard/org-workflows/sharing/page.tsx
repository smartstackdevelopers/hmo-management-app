import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, Td, Th } from "@/components/ui/primitives";
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
    return <EmptyState title="Unavailable" description="Select the organisation you're working in." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  let items: Array<Record<string, unknown>> = [];
  try {
    items = (await listSharingGrants({ accessToken: token, organisationId: orgId, role: session.authorization?.active_role })).items;
  } catch {
    return <ErrorState description={"Failed to load grants"} />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader eyebrow="Operations" title="Secure sharing" description="Active grants only. A share link is shown once, when it is created." />
      {items.length === 0 ? (
        <EmptyState title="No active grants" description="Active sharing grants will appear here." />
      ) : (
        <DataTable caption="Secure sharing grants">
          <thead>
            <tr>
              <Th>Reference</Th>
              <Th>Resource</Th>
              <Th>Expires</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((g) => (
              <tr key={String(g.id)}>
                <Td className="font-semibold text-slate-900">{String(g.reference_number)}</Td>
                <Td>{String(g.resource_type)}</Td>
                <Td className="whitespace-nowrap text-slate-500">{String(g.expires_at)}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">Showing {items.length === 0 ? "0" : `1–${items.length}`} of {items.length}</p>
    </div>
  );
}
