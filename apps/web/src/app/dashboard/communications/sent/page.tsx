import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 for the web app." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }
  let rows: Array<Record<string, unknown>> = [];
  let err: string | null = null;
  try {
    const data = await listSent({ accessToken: token, organisationId: orgId, role: session.authorization.active_role });
    rows = data.items;
  } catch (e) {
    err = e instanceof Error ? e.message : "Failed";
  }
  if (err) {
    return <ErrorState description={err} />;
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="F2.12" title="Sent messages" description="GET /api/v1/communications/messages/sent" />
      {rows.length === 0 ? (
        <p className="text-slate-600">No sent messages.</p>
      ) : (
        <ul className="divide-y rounded border border-slate-200 bg-white">
          {rows.map((r) => (
            <li key={String(r.message_id)} className="px-4 py-3">
              <div className="font-medium">{String(r.subject || "(no subject)")}</div>
              <div className="text-sm text-slate-600">{String(r.body_preview || "")}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
