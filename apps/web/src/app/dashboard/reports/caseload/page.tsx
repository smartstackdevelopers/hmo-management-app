import { redirect } from "next/navigation";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { canAny } from "@/lib/rbac";
import { exportReportUrl } from "@/lib/reportingApi";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function CaseloadReportsPage() {
  const session = await requireAuthenticatedSession("/dashboard/reports/caseload");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["reports.caseload.view", "reports.read"])
  ) {
    redirect("/unauthorized");
  }
  return (
    <div className="space-y-6">
      <PageHeader
        title="Caseload reports"
        description="Assignment counts only — not staff performance scoring."
      />
      <p className="text-sm text-slate-600">CSV export path: {exportReportUrl("caseload", "csv")}</p>
    </div>
  );
}
