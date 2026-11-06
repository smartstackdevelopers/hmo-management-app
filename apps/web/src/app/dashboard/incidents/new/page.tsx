import { redirect } from "next/navigation";
import { IncidentForm } from "@/components/incidents/IncidentForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewIncidentPage() {
  const session = await requireAuthenticatedSession("/dashboard/incidents/new");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "incidents.manage",
      "incidents.create.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot create incident." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Access token unavailable" description="Sign in again." />;
  }
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader eyebrow="F2.4" title="New incident" description="Report an operational incident." />
      <IncidentForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
      />
    </div>
  );
}
