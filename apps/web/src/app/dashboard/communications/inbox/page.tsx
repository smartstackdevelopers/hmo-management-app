import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listInbox } from "@/lib/communicationsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function InboxPage() {
  const session = await requireAuthenticatedSession("/dashboard/communications/inbox");
  if (!session.authorization || !canAny(session.authorization.permissions, ["communication.messages.read"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Select an organisation." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 for the web app." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }
  let rows: Array<Record<string, unknown>> = [];
  let total = 0;
  let err: string | null = null;
  try {
    const data = await listInbox({ accessToken: token, organisationId: orgId, role: session.authorization.active_role });
    rows = data.items;
    total = data.total;
  } catch (e) {
    err = e instanceof Error ? e.message : "Failed";
  }
  if (err) {
    return <ErrorState description={err} />;
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="F2.12" title="Inbox" description={`${total} message(s) — GET /api/v1/communications/messages/inbox`} />
      {rows.length === 0 ? (
        <p className="text-slate-600">No messages.</p>
      ) : (
        <ul className="divide-y rounded border border-slate-200 bg-white">
          {rows.map((r) => (
            <li key={String(r.recipient_id)} className="px-4 py-3">
              <div className="font-medium">{String(r.subject || "(no subject)")}</div>
              <div className="text-sm text-slate-600">{String(r.body_preview || "")}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
