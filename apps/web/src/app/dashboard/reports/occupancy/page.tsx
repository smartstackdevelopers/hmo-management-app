import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { ReportCategoryPanel } from "@/components/reports/ReportCategoryPanel";
import { requireReportAccess } from "../_reportAuth";

export default async function OccupancyReportsPage() {
  const { session, token, orgId } = await requireReportAccess("/dashboard/reports/occupancy", [
    "reports.occupancy.view",
  ]);
  if (!orgId) return <EmptyState title="Unavailable" description="Organisation context required." />;
  if (!token) return <ErrorState description="Access token unavailable." />;
  return (
    <ReportCategoryPanel
      category="occupancy"
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      title="Occupancy reports"
      description="Property, building and room occupancy using the same assignment math as landlord enterprise tools."
    />
  );
}
