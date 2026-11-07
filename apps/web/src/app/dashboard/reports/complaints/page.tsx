import { redirect } from "next/navigation";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { canAny } from "@/lib/rbac";
import { exportReportUrl } from "@/lib/reportingApi";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function ComplaintsReportsPage() {
  const session = await requireAuthenticatedSession("/dashboard/reports/complaints");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["reports.complaints.view", "reports.read"])
  ) {
    redirect("/unauthorized");
  }
  return (
    <div className="space-y-6">
      <PageHeader
        title="Complaints reports"
        description="Operational deadlines from organisation rules — not statutory response periods."
      />
      <p className="text-sm text-slate-600">CSV export path: {exportReportUrl("complaints", "csv")}</p>
    </div>
  );
}
