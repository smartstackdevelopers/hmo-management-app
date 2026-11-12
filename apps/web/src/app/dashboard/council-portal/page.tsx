import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { CouncilPortalDashboard } from "@/components/council/CouncilPortalDashboard";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function CouncilPortalPage() {
  const session = await requireAuthenticatedSession("/dashboard/council-portal");
  const perms = session.authorization?.permissions ?? [];
  const canManage = canAny(perms, ["council_portal.manage"]);
  // Officers may not have a core manage permission — page still loads; API enforces officer grant.
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  // Block tenants explicitly
  if (session.authorization?.active_role === "tenant") {
    redirect("/unauthorized");
  }
  return (
    <CouncilPortalDashboard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canManage}
    />
  );
}
