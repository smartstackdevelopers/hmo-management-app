import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th } from "@/components/ui/primitives";
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
    return <EmptyState title="Unavailable" description="Select the organisation you're working in." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
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
  } catch {
    return <ErrorState description={"Failed to load forms"} />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader eyebrow="Operations" title="Custom forms" description="Organisation forms with versioned schemas." />
      {items.length === 0 ? (
        <EmptyState title="No forms" description="Forms published for this organisation will appear here." />
      ) : (
        <DataTable caption="Custom forms">
          <thead>
            <tr>
              <Th>Form</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((form) => (
              <tr key={String(form.id)}>
                <Td className="font-semibold text-slate-900">{String(form.title)}</Td>
                <Td>
                  <StatusChip status={String(form.status)} />
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
