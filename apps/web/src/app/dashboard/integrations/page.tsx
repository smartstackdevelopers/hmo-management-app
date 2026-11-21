import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { IntegrationsBoard } from "./IntegrationsBoard";

const READ = ["integrations.read", "integrations.manage"];

export default async function IntegrationsPage() {
  const session = await requireAuthenticatedSession("/dashboard/integrations");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see integrations." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so integrations can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/integrations" />;
  const canManage = canAny(session.authorization?.permissions ?? [], ["integrations.manage"]);
  return (
    <IntegrationsBoard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canManage}
    />
  );
}
