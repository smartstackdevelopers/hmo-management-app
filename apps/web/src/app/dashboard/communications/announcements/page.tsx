import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listAnnouncements } from "@/lib/communicationsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function AnnouncementsPage() {
  const session = await requireAuthenticatedSession("/dashboard/communications/announcements");
  if (!session.authorization || !canAny(session.authorization.permissions, ["communication.announcements.read"])) {
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
    rows = await listAnnouncements({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization.active_role,
    });
  } catch {
    err = "We could not load this page. Please try again.";
  }
  if (err) {
    return <ErrorState description={err} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Communications" title="Announcements" description="Published announcements visible to your role." />
      {rows.length === 0 ? (
        <EmptyState title="No announcements" description="Nothing has been published for your role." />
      ) : (
        <DataTable caption="Announcements">
          <thead>
            <tr>
              <Th>Title</Th>
              <Th>Reference</Th>
              <Th>Priority</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={String(a.id)} className="hover:bg-slate-50">
                <Td className="font-semibold text-slate-900">{String(a.title)}</Td>
                <Td className="text-slate-500">{String(a.reference_number || "—")}</Td>
                <Td>
                  {a.priority ? <StatusChip status={String(a.priority)} /> : "—"}
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}
