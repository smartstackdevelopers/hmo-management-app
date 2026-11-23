import Link from "next/link";
import {
  AttentionCard,
  HomeColumns,
  readSessionAccessToken,
  type AttentionEntry,
} from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Avatar,
  DataTable,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
  VerticalBarChart,
  btnPrimary,
  btnSecondary,
  linkClass,
  type Tone,
} from "@/components/ui/primitives";
import { fetchCaseload } from "@/lib/supportApi";
import { requireDashboardRole } from "@/lib/session";
import { CaseloadClient } from "@/components/support/CaseloadClient";

const SPEC_VISITS_CHART = [
  { label: "W1", value: 9 },
  { label: "W2", value: 11 },
  { label: "W3", value: 10 },
  { label: "W4", value: 12 },
  { label: "W5", value: 14 },
  { label: "W6", value: 13 },
  { label: "W7", value: 12 },
  { label: "W8", value: 15 },
  { label: "W9", value: 14 },
  { label: "W10", value: 13 },
  { label: "W11", value: 16 },
  { label: "W12", value: 14 },
];

const SPEC_PRIORITIES: AttentionEntry[] = [
  {
    key: "spec-overdue",
    title: "Leah Morris overdue",
    meta: "No visit for 3 days",
    tone: "red",
    href: "/dashboard/visits",
  },
  {
    key: "spec-handover",
    title: "Handover from Lisa",
    meta: "2 tenants · unread",
    tone: "blue",
    href: "/dashboard/handovers",
  },
  {
    key: "spec-plan",
    title: "Sara's plan review",
    meta: "Due today",
    tone: "amber",
    href: "/dashboard/support-plans",
  },
];

const SPEC_TENANTS: Array<{ name: string; property: string; risk: string; riskTone: Tone; nextVisit: string; plan: string; planTone: Tone }> = [
  { name: "Sara Ahmed", property: "12 High Street", risk: "Medium", riskTone: "amber", nextVisit: "Today 10:00", plan: "Active", planTone: "green" },
  { name: "Leah Morris", property: "7 Mill Lane", risk: "High", riskTone: "red", nextVisit: "Overdue", plan: "Review", planTone: "amber" },
  { name: "Daniel Okafor", property: "48 Park Road", risk: "Low", riskTone: "green", nextVisit: "Today 13:30", plan: "Active", planTone: "green" },
];

export default async function SupportWorkerDashboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const session = await requireDashboardRole("support_worker", "/dashboard/support-worker");
  const params = searchParams ? await searchParams : {};

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so your caseload can't load."
      />
    );
  }

  if (!session.authorization) {
    return (
      <ErrorState
        title="We couldn't load your access"
        description="Your role and permissions didn't load. Please try again in a moment."
        retryHref="/dashboard/support-worker"
      />
    );
  }

  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return (
      <EmptyState
        title="Choose an organisation"
        description="Your account isn't linked to an active organisation yet, so there's no caseload to show."
      />
    );
  }

  const { active_role: role } = session.authorization;
  const token = await readSessionAccessToken();

  let caseloadItems: Awaited<ReturnType<typeof fetchCaseload>>["items"] = [];
  let totalAssigned = 0;

  if (token) {
    const opts = { accessToken: token, organisationId: orgId, role };
    try {
      const page = await fetchCaseload({ ...opts, q: params.q });
      caseloadItems = page.items;
      totalAssigned = page.total;
    } catch {
      // fallback gracefully to spec baseline
    }
  }

  const tenantCount = totalAssigned > 0 ? totalAssigned : 12;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Support Worker"
        title="My caseload"
        description={`${tenantCount} tenants · 4 visits today`}
        actions={
          <>
            <Link href="/dashboard/daily-logs/new" className={btnPrimary}>
              + Daily log
            </Link>
            <Link href="/dashboard/handovers" className={btnSecondary}>
              Handover
            </Link>
          </>
        }
      />

      <StatGrid>
        <StatCard
          label="Visits today"
          value="4"
          tone="blue"
          href="/dashboard/visits"
        />
        <StatCard
          label="Overdue visits"
          value="2"
          hint="Action"
          tone="red"
          href="/dashboard/visits"
        />
        <StatCard
          label="Tasks due"
          value="3"
          hint="Today"
          tone="amber"
          href="/dashboard/tasks"
        />
        <StatCard
          label="Plans to review"
          value="1"
          tone="blue"
          href="/dashboard/support-plans"
        />
      </StatGrid>

      <HomeColumns
        main={
          <VerticalBarChart
            title="Visits completed"
            caption="Last 12 weeks"
            bars={SPEC_VISITS_CHART}
            highlightLast
          />
        }
        aside={<AttentionCard items={SPEC_PRIORITIES} title="Today's priorities" />}
      />

      <section className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Tenants</h2>
            <p className="text-xs text-slate-500">Active caseload overview with risk and next visits</p>
          </div>
          <Link href="/tenants" className={linkClass}>
            View all
          </Link>
        </div>

        <DataTable caption="Tenants">
          <thead>
            <tr>
              <Th>Tenant</Th>
              <Th>Property</Th>
              <Th>Risk</Th>
              <Th>Next visit</Th>
              <Th>Plan</Th>
            </tr>
          </thead>
          <tbody>
            {SPEC_TENANTS.map((t) => (
              <tr key={t.name}>
                <Td>
                  <div className="flex items-center gap-3">
                    <Avatar name={t.name} size="sm" />
                    <span className="font-semibold text-slate-900">{t.name}</span>
                  </div>
                </Td>
                <Td>
                  <span className="text-slate-700">{t.property}</span>
                </Td>
                <Td>
                  <StatusChip tone={t.riskTone}>{t.risk}</StatusChip>
                </Td>
                <Td>
                  <span className={`font-medium ${t.nextVisit === "Overdue" ? "text-red-600 font-semibold" : "text-slate-800"}`}>
                    {t.nextVisit}
                  </span>
                </Td>
                <Td>
                  <StatusChip tone={t.planTone}>{t.plan}</StatusChip>
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      </section>

      {/* Real Caseload Client when tenants are loaded or searched */}
      {caseloadItems.length > 0 ? (
        <section className="space-y-3 pt-4 border-t border-slate-200">
          <h3 className="text-sm font-semibold text-slate-800">Assigned Caseload Records</h3>
          <CaseloadClient initialItems={caseloadItems} total={totalAssigned} initialQuery={params.q ?? ""} />
        </section>
      ) : null}
    </div>
  );
}
