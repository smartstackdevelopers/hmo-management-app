import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { IntegrationsDashboard } from "@/components/integrations/IntegrationsDashboard";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = ["integrations.read", "integrations.manage"];

export default async function IntegrationsPage() {
  const session = await requireAuthenticatedSession("/dashboard/integrations");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const canManage = canAny(session.authorization?.permissions ?? [], ["integrations.manage"]);
  return (
    <IntegrationsDashboard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canManage}
    />
  );
}
