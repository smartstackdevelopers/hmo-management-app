import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { getPreferences } from "@/lib/communicationsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function PreferencesPage() {
  const session = await requireAuthenticatedSession("/dashboard/communications/preferences");
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
  let prefs: Record<string, unknown> | null = null;
  let err: string | null = null;
  try {
    prefs = await getPreferences({
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
      <PageHeader eyebrow="F2.12" title="Communication preferences" description="GET /api/v1/communications/preferences" />
      <dl className="grid gap-2 rounded border border-slate-200 bg-white p-4 text-sm sm:grid-cols-2">
        {Object.entries(prefs || {}).map(([k, v]) => (
          <div key={k}>
            <dt className="text-slate-500">{k}</dt>
            <dd className="font-medium">{String(v)}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-slate-500">Updates use PATCH /api/v1/communications/preferences (not wired in this shell).</p>
    </div>
  );
}
