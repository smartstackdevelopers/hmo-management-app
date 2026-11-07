import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 for the web app." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }
  let rows: Array<Record<string, unknown>> = [];
  let err: string | null = null;
  try {
    rows = await listAnnouncements({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization.active_role,
    });
  } catch (e) {
    err = e instanceof Error ? e.message : "Failed";
  }
  if (err) {
    return <ErrorState description={err} />;
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="F2.12" title="Announcements" description="Published announcements visible to your role" />
      {rows.length === 0 ? (
        <p className="text-slate-600">No announcements.</p>
      ) : (
        <ul className="divide-y rounded border border-slate-200 bg-white">
          {rows.map((a) => (
            <li key={String(a.id)} className="px-4 py-3">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-medium">{String(a.title)}</span>
                {a.priority === "emergency" ? (
                  <span className="rounded bg-red-100 px-2 text-xs text-red-900">Emergency</span>
                ) : null}
              </div>
              <div className="text-xs text-slate-500">{String(a.reference_number || "")}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
