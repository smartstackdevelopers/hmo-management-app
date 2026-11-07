import { redirect } from "next/navigation";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { exportReportUrl } from "@/lib/reportingApi";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function HousingReportsPage() {
  const session = await requireAuthenticatedSession("/dashboard/reports/housing");
  if (session.authorization && !canAny(session.authorization.permissions, ["reports.housing.view", "reports.read"])) {
    redirect("/unauthorized");
  }
  const base = exportReportUrl("housing", "csv");
  return (
    <div className="space-y-6">
      <PageHeader title="Housing application reports" description="F2.5 records; filters via API query params." />
      <p className="text-sm text-slate-600">
        Export (requires token in browser session): use API{" "}
        <code className="text-xs">GET /api/v1/reports/housing/summary</code> and exports at{" "}
        <code className="text-xs">{base}</code> with Authorization header.
      </p>
      {!isAuth0Configured() || !auth0 ? (
        <p className="text-sm text-amber-800">Auth0 not configured — exports unavailable in UI.</p>
      ) : null}
    </div>
  );
}
