import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { ReportCategoryPanel } from "@/components/reports/ReportCategoryPanel";
import { requireReportAccess } from "../_reportAuth";

export default async function CaseloadReportsPage() {
  const { session, token, orgId } = await requireReportAccess("/dashboard/reports/caseload", [
    "reports.caseload.view",
  ]);
  if (!orgId) return <EmptyState title="Unavailable" description="Organisation context required." />;
  if (!token) return <ErrorState description="Access token unavailable." />;
  return (
    <ReportCategoryPanel
      category="caseload"
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      title="Staff caseload reports"
      description="Assigned tenants, active cases, pending tasks and overdue follow-ups by support worker."
    />
  );
}
