import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PrivacyDashboard } from "@/components/privacy/PrivacyDashboard";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = ["privacy.read", "privacy.manage"];

export default async function PrivacyPage() {
  const session = await requireAuthenticatedSession("/dashboard/privacy");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const canManage = canAny(session.authorization?.permissions ?? [], ["privacy.manage"]);
  return (
    <PrivacyDashboard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canManage}
    />
  );
}
