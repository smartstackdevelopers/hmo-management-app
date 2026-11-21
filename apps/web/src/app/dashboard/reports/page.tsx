import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnSecondary, DataTable, FilterTabs, inputClass, linkClass, StatCard, StatGrid, Td, Th } from "@/components/ui/primitives";
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

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : undefined;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function headline(block: Record<string, unknown> | undefined): number | string {
  if (!block) return "—";
  if (typeof block.total === "number") return block.total;
  if (typeof block.total_rooms === "number") return block.total_rooms;
  if (typeof block.open_total === "number") return block.open_total;
  return "—";
}

export default async function ReportsDashboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
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
  const visibleNav = NAV.filter((item) => canAny(perms, [item.perm, "reports.read"]));
  const canSchedule = canAny(perms, ["reports.schedule.manage", "reports.read"]);
  const q = (params.q ?? "").trim().toLowerCase();
  const occupancy = asRecord(data.occupancy);
  const complaints = asRecord(data.complaints);
  const occupancyRate = asNumber(occupancy?.occupancy_rate);
  const complaintsOpen = asNumber(complaints?.open_complaints);
  const availableRows = [
    { key: "housing", label: "Housing applications", href: "/dashboard/reports/housing" },
    { key: "complaints", label: "Complaints", href: "/dashboard/reports/complaints" },
    { key: "caseload", label: "Support caseload", href: "/dashboard/reports/caseload" },
    { key: "occupancy", label: "Occupancy", href: "/dashboard/reports/occupancy" },
    { key: "plans", label: "Support plans", href: "/dashboard/reports/plans" },
    { key: "alerts", label: "Open alerts", href: "/dashboard/reports/alerts" },
  ]
    .map((row) => ({ ...row, block: asRecord(data[row.key]), value: headline(asRecord(data[row.key])) }))
    .filter((row) => row.block);
  const rows = availableRows.filter((row) => !q || row.label.toLowerCase().includes(q));
  const updated = typeof data.generated_at === "string" ? data.generated_at : "";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Insights"
        title="Reports"
        description="Housing, caseload, complaints and occupancy insights."
        actions={
          canSchedule ? (
            <Link href="/dashboard/reports/schedules" className={btnSecondary}>
              Schedule
            </Link>
          ) : null
        }
      />
      {updated ? <p className="text-sm text-slate-500">Last updated: {updated}</p> : null}
      <div className="flex flex-wrap items-center gap-3">
        <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
          <label className="sr-only" htmlFor="report-search">
            Search reports
          </label>
          <input
            id="report-search"
            name="q"
            defaultValue={params.q ?? ""}
            placeholder="Search reports"
            className={inputClass}
          />
          <button type="submit" className={btnSecondary}>
            Search
          </button>
        </form>
        {visibleNav.length > 0 ? <FilterTabs tabs={visibleNav.map((item) => ({ label: item.label, href: item.href }))} /> : null}
      </div>
      {occupancyRate != null || complaintsOpen != null ? (
        <StatGrid>
          {occupancyRate != null ? <StatCard label="Occupancy" value={`${occupancyRate}%`} href="/dashboard/reports/occupancy" /> : null}
          {complaintsOpen != null ? <StatCard label="Complaints open" value={complaintsOpen} href="/dashboard/reports/complaints" /> : null}
        </StatGrid>
      ) : null}
      {rows.length === 0 ? (
        <EmptyState
          title="No report sections"
          description={q ? "No report matches this search." : "Report sections appear when your role can view them."}
          action={q ? { label: "Clear search", href: "/dashboard/reports" } : undefined}
        />
      ) : (
        <DataTable caption="Reports">
          <thead>
            <tr>
              <Th>Report</Th>
              <Th>Total</Th>
              <Th>Updated</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="hover:bg-slate-50/60">
                <Td>
                  <Link href={row.href} className={linkClass}>
                    {row.label}
                  </Link>
                </Td>
                <Td className="tabular-nums">{row.value}</Td>
                <Td>{typeof row.block?.generated_at === "string" ? row.block.generated_at : updated || "—"}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-sm text-slate-500">
        {rows.length === 0 ? `Showing 0 of ${availableRows.length}` : `Showing 1–${rows.length} of ${availableRows.length}`}
      </p>
    </div>
  );
}
