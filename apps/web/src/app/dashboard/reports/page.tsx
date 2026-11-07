import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { fetchReportingDashboard } from "@/lib/reportingApi";
import { requireAuthenticatedSession } from "@/lib/session";

const ANY = [
  "reports.dashboard.view",
  "reports.housing.view",
  "reports.complaints.view",
  "reports.caseload.view",
  "reports.read",
];

export default async function ReportsDashboardPage() {
  const session = await requireAuthenticatedSession("/dashboard/reports");
  if (session.authorization && !canAny(session.authorization.permissions, ANY)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  let data: Record<string, unknown>;
  try {
    data = await fetchReportingDashboard({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load reports"} />;
  }

  const section = (key: string, label: string) => {
    const block = data[key] as Record<string, unknown> | undefined;
    if (!block) return null;
    const total = typeof block.total === "number" ? block.total : "—";
    return (
      <div key={key} className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="text-sm text-slate-600">{label}</div>
        <div className="text-2xl font-semibold">{total}</div>
        <Link className="text-sm text-blue-700 underline" href={`/dashboard/reports/${key}`}>
          View details
        </Link>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="F2.14"
        title="Operational reporting"
        description="Metrics from live database aggregates — not statutory compliance reporting."
      />
      <p className="text-sm text-slate-600">Last updated: {String(data.generated_at ?? "")}</p>
      <div className="grid gap-3 sm:grid-cols-3">
        {section("housing", "Housing applications")}
        {section("complaints", "Complaints")}
        {section("caseload", "Support caseload")}
      </div>
    </div>
  );
}
