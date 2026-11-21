import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, humanize } from "@/components/ui/primitives";
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
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  }
  let prefs: Record<string, unknown> | null = null;
  let err: string | null = null;
  try {
    prefs = await getPreferences({
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

  const entries = Object.entries(prefs || {});
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Communications" title="Communication preferences" description="How this organisation reaches you." />
      {entries.length === 0 ? (
        <EmptyState title="No preferences" description="No communication preferences were returned." />
      ) : (
        <Card>
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            {entries.map(([k, v]) => (
              <div key={k}>
                <dt className="text-slate-500">{humanize(k)}</dt>
                <dd className="mt-0.5 font-medium text-slate-900">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}
      <p className="text-xs text-slate-500">These preferences are read-only on this page.</p>
    </div>
  );
}
