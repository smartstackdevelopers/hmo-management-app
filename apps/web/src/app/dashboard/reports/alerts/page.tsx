import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { AlertsPanel } from "@/components/reports/AlertsPanel";
import { canAny } from "@/lib/rbac";
import { requireReportAccess } from "../_reportAuth";

export default async function AlertsPage() {
  const { session, token, orgId } = await requireReportAccess("/dashboard/reports/alerts", [
    "reports.alerts.view",
  ]);
  if (!orgId) return <EmptyState title="Unavailable" description="Organisation context required." />;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const canManage = canAny(session.authorization?.permissions ?? [], ["reports.schedule.manage"]);
  return (
    <AlertsPanel
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canManage}
    />
  );
}
