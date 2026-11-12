import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { ReportCategoryPanel } from "@/components/reports/ReportCategoryPanel";
import { requireReportAccess } from "../_reportAuth";

export default async function PlansReportsPage() {
  const { session, token, orgId } = await requireReportAccess("/dashboard/reports/plans", [
    "reports.plans.view",
  ]);
  if (!orgId) return <EmptyState title="Unavailable" description="Organisation context required." />;
  if (!token) return <ErrorState description="Access token unavailable." />;
  return (
    <ReportCategoryPanel
      category="plans"
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      title="Support plan completion reports"
      description="Active and completed plans, overdue reviews and goal completion rates from F2.10 records."
    />
  );
}
