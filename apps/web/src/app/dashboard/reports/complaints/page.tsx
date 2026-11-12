import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { ReportCategoryPanel } from "@/components/reports/ReportCategoryPanel";
import { requireReportAccess } from "../_reportAuth";

export default async function ComplaintsReportsPage() {
  const { session, token, orgId } = await requireReportAccess("/dashboard/reports/complaints", [
    "reports.complaints.view",
  ]);
  if (!orgId) return <EmptyState title="Unavailable" description="Organisation context required." />;
  if (!token) return <ErrorState description="Access token unavailable." />;
  return (
    <ReportCategoryPanel
      category="complaints"
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      title="Complaints reports"
      description="Open, resolved and overdue complaints with priority and category distributions from operational records."
    />
  );
}
