import { redirect } from "next/navigation";
import { BackupMonitoringDashboard } from "@/components/backups/BackupMonitoringDashboard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = ["backup.read", "backup.manage"];

export default async function BackupsPage() {
  const session = await requireAuthenticatedSession("/dashboard/backups");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const canManage = canAny(session.authorization?.permissions ?? [], ["backup.manage"]);
  return (
    <BackupMonitoringDashboard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canManage}
    />
  );
}
