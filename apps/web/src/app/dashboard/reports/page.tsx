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
  "reports.occupancy.view",
  "reports.plans.view",
  "reports.read",
];

const NAV = [
  { key: "housing", label: "Housing applications", href: "/dashboard/reports/housing", perm: "reports.housing.view" },
  { key: "complaints", label: "Complaints", href: "/dashboard/reports/complaints", perm: "reports.complaints.view" },
  { key: "caseload", label: "Staff caseload", href: "/dashboard/reports/caseload", perm: "reports.caseload.view" },
  { key: "occupancy", label: "Occupancy", href: "/dashboard/reports/occupancy", perm: "reports.occupancy.view" },
  { key: "plans", label: "Support plans", href: "/dashboard/reports/plans", perm: "reports.plans.view" },
  { key: "schedules", label: "Scheduled reports", href: "/dashboard/reports/schedules", perm: "reports.schedule.manage" },
  { key: "alerts", label: "Early-warning alerts", href: "/dashboard/reports/alerts", perm: "reports.alerts.view" },
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

  const perms = session.authorization?.permissions ?? [];
  const section = (key: string, label: string) => {
    const block = data[key] as Record<string, unknown> | undefined;
    if (!block) return null;
    const total =
      typeof block.total === "number"
        ? block.total
        : typeof block.total_rooms === "number"
          ? block.total_rooms
          : typeof block.open_total === "number"
            ? block.open_total
            : "—";
    return (
      <div key={key} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm text-slate-600">{label}</div>
        <div className="text-2xl font-semibold text-slate-900">{total}</div>
        <Link className="text-sm text-teal-800 underline" href={`/dashboard/reports/${key === "alerts" ? "alerts" : key}`}>
          View details
        </Link>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="F6.2"
        title="Reports & analytics"
        description="Live organisation metrics from PostgreSQL — occupancy, housing, complaints, caseload, and support plans."
      />
      <p className="text-sm text-slate-600">Last updated: {String(data.generated_at ?? "")}</p>

      <nav className="flex flex-wrap gap-2">
        {NAV.filter((n) => canAny(perms, [n.perm, "reports.read"])).map((n) => (
          <Link
            key={n.key}
            href={n.href}
            className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 hover:bg-slate-50"
          >
            {n.label}
          </Link>
        ))}
      </nav>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {section("housing", "Housing applications")}
        {section("complaints", "Complaints")}
        {section("caseload", "Support caseload")}
        {section("occupancy", "Occupancy rooms")}
        {section("plans", "Support plans")}
        {section("alerts", "Open alerts")}
      </div>
    </div>
  );
}
