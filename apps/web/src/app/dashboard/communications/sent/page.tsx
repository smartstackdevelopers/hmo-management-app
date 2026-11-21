import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listSent } from "@/lib/communicationsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function SentPage() {
  const session = await requireAuthenticatedSession("/dashboard/communications/sent");
  if (!session.authorization || !canAny(session.authorization.permissions, ["communication.messages.read"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  }
  let rows: Array<Record<string, unknown>> = [];
  let err: string | null = null;
  try {
    const data = await listSent({ accessToken: token, organisationId: orgId, role: session.authorization.active_role });
    rows = data.items;
  } catch {
    err = "We could not load this page. Please try again.";
  }
  if (err) {
    return <ErrorState description={err} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Communications" title="Sent messages" description="Messages you have sent in this organisation." />
      {rows.length === 0 ? (
        <EmptyState title="Nothing sent" description="No sent messages." />
      ) : (
        <DataTable caption="Sent messages">
          <thead>
            <tr>
              <Th>Subject</Th>
              <Th>Preview</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={String(r.message_id)} className="hover:bg-slate-50">
                <Td className="font-semibold text-slate-900">{String(r.subject || "(no subject)")}</Td>
                <Td className="max-w-md truncate text-slate-600">{String(r.body_preview || "")}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}
