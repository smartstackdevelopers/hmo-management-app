import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { ReportCategoryPanel } from "@/components/reports/ReportCategoryPanel";
import { requireReportAccess } from "../_reportAuth";

export default async function HousingReportsPage() {
  const { session, token, orgId } = await requireReportAccess("/dashboard/reports/housing", [
    "reports.housing.view",
  ]);
  if (!orgId) return <EmptyState title="Unavailable" description="Organisation context required." />;
  if (!token) return <ErrorState description="Access token unavailable." />;
  return (
    <ReportCategoryPanel
      category="housing"
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      title="Housing application reports"
      description="Totals, pending/approved/rejected, waiting list, property breakdown and processing trends from live applications."
    />
  );
}
