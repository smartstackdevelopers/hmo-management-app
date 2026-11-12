import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { SchedulesPanel } from "@/components/reports/SchedulesPanel";
import { requireReportAccess } from "../_reportAuth";

export default async function SchedulesPage() {
  const { session, token, orgId } = await requireReportAccess("/dashboard/reports/schedules", [
    "reports.schedule.manage",
  ]);
  if (!orgId) return <EmptyState title="Unavailable" description="Organisation context required." />;
  if (!token) return <ErrorState description="Access token unavailable." />;
  return (
    <SchedulesPanel
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
    />
  );
}
