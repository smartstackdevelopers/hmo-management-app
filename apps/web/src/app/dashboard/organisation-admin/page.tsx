import Link from "next/link";
import {
  AttentionCard,
  HomeColumns,
  greeting,
  readSessionAccessToken,
  todayLabel,
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
} from "@/components/ui/primitives";
import { fetchMaintenanceDashboard, type MaintenanceDashboard } from "@/lib/maintenanceApi";
import { fetchOrgWorkflowsDashboard } from "@/lib/orgWorkflowsApi";
import { canAny } from "@/lib/rbac";
import { getSafeguardingDashboard } from "@/lib/safeguardingAlertsApi";
import { requireDashboardRole } from "@/lib/session";

const MAINTENANCE_READ = [
  "maintenance.manage",
  "maintenance.read.own",
  "maintenance.read.assigned",
  "maintenance.create.own",
  "maintenance.create.assigned",
  "maintenance.read.property",
];
const WORKFLOWS_READ = ["approvals.inbox.read", "organisation.workflows.manage", "organisation.forms.manage"];
const SAFEGUARDING_READ = ["safeguarding_alerts.read", "safeguarding_alerts.manage"];

const SPEC_REPAIRS_CHART = [
  { label: "Dec", value: 14 },
  { label: "Jan", value: 18 },
  { label: "Feb", value: 12 },
  { label: "Mar", value: 20 },
  { label: "Apr", value: 16 },
  { label: "May", value: 22 },
  { label: "Jun", value: 19 },
  { label: "Jul", value: 24 },
  { label: "Aug", value: 21 },
  { label: "Sep", value: 18 },
  { label: "Oct", value: 23 },
  { label: "Nov", value: 17 },
];

const SPEC_ATTENTION: AttentionEntry[] = [
  {
    key: "spec-alert",
    title: "Safeguarding alert",
    meta: "Leah Morris · missed check-ins",
    tone: "red",
    href: "/dashboard/safeguarding-alerts",
  },
  {
    key: "spec-rota",
    title: "Rota gap Friday",
    meta: "2 shifts uncovered",
    tone: "amber",
    href: "/dashboard/rota",
  },
  {
    key: "spec-reg",
    title: "3 registrations",
    meta: "Waiting for approval",
    tone: "amber",
    href: "/dashboard/approvals/registrations",
  },
  {
    key: "spec-gas",
    title: "Gas certificate due",
    meta: "7 Mill Lane · 12 days",
    tone: "amber",
    href: "/dashboard/documents",
  },
];

const STAFF_WORKLOAD = [
  { name: "Amir Hassan", role: "Support worker", caseload: "12", visits: "14", status: "On track", tone: "green" },
  { name: "Lisa Grant", role: "Support worker", caseload: "15", visits: "9", status: "Overloaded", tone: "red" },
  { name: "Kevin Brooks", role: "Contractor", caseload: "7 jobs", visits: "—", status: "On track", tone: "green" },
];

function numberField(source: Record<string, unknown> | null, key: string): number | null {
  const value = source?.[key];
  return typeof value === "number" ? value : null;
}

export default async function OrganisationAdminDashboardPage() {
  const session = await requireDashboardRole(
    "organisation_admin",
    "/dashboard/organisation-admin",
  );

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so your organisation overview can't load."
      />
    );
  }

  if (!session.authorization) {
    return (
      <ErrorState
        title="We couldn't load your access"
        description="Your role and permissions didn't load. Please try again in a moment."
        retryHref="/dashboard/organisation-admin"
      />
    );
  }

  const { permissions, active_role: role, active_organisation_id: orgId } = session.authorization;

  let maintenance: MaintenanceDashboard | null = null;
  let workflows: Record<string, unknown> | null = null;
  let safeguarding: Record<string, unknown> | null = null;

  if (orgId) {
    const token = await readSessionAccessToken();
    if (token) {
      const opts = { accessToken: token, organisationId: orgId, role };
      [maintenance, workflows, safeguarding] = await Promise.all([
        canAny(permissions, MAINTENANCE_READ) ? fetchMaintenanceDashboard(opts).catch(() => null) : null,
        canAny(permissions, WORKFLOWS_READ) ? fetchOrgWorkflowsDashboard(opts).catch(() => null) : null,
        canAny(permissions, SAFEGUARDING_READ) ? getSafeguardingDashboard(token, orgId).catch(() => null) : null,
      ]);
    }
  }

  const pendingApprovals = numberField(workflows, "pending_approvals");
  const criticalAlerts = numberField(safeguarding, "critical_open");

  const liveAttention: AttentionEntry[] = [];
  if (criticalAlerts) {
    liveAttention.push({
      key: "safeguarding-critical",
      title: `${criticalAlerts} critical safeguarding alert${criticalAlerts === 1 ? "" : "s"}`,
      meta: "Open and waiting for review",
      tone: "red",
      href: "/dashboard/safeguarding-alerts",
    });
  }
  if (maintenance?.urgent_and_emergency) {
    liveAttention.push({
      key: "repairs-urgent",
      title: `${maintenance.urgent_and_emergency} urgent repair${maintenance.urgent_and_emergency === 1 ? "" : "s"}`,
      meta: "Urgent or emergency priority",
      tone: "red",
      href: "/dashboard/maintenance",
    });
  }

  const attentionItems = liveAttention.length > 0
    ? [...liveAttention, ...SPEC_ATTENTION.slice(0, Math.max(1, 4 - liveAttention.length))]
    : SPEC_ATTENTION;

  const userGreeting = greeting(session.user?.name) ?? "Good morning, Helen";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Organisation Admin"
        title={userGreeting}
        description={`Demo Housing · ${todayLabel()}`}
        actions={
          <>
            <Link href="/dashboard/approvals/registrations" className={btnPrimary}>
              + Invite staff
            </Link>
            <Link href="/dashboard/reports" className={btnSecondary}>
              Reports
            </Link>
          </>
        }
      />

      <StatGrid>
        <StatCard
          label="Tenants"
          value="48"
          hint="+3"
          tone="green"
          href="/tenants"
        />
        <StatCard
          label="Occupancy"
          value="92%"
          hint="+2%"
          tone="green"
          href="/dashboard/room-occupancy"
        />
        <StatCard
          label="Open repairs"
          value={maintenance?.open_count ?? 11}
          hint={maintenance?.urgent_and_emergency ? `${maintenance.urgent_and_emergency} urgent` : "4 urgent"}
          tone="red"
          href="/dashboard/maintenance"
        />
        <StatCard
          label="Approvals"
          value={pendingApprovals ?? 6}
          hint="Review"
          tone="amber"
          href="/dashboard/approvals/registrations"
        />
      </StatGrid>

      <HomeColumns
        main={
          <VerticalBarChart
            title="Repairs opened vs closed"
            caption="Last 12 months"
            bars={SPEC_REPAIRS_CHART}
            highlightLast
          />
        }
        aside={<AttentionCard items={attentionItems} />}
      />

      <section className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Staff workload</h2>
            <p className="text-xs text-slate-500">Caseload and weekly visits across your frontline team</p>
          </div>
          <Link href="/dashboard/workload" className={linkClass}>
            View all
          </Link>
        </div>

        <DataTable caption="Staff workload">
          <thead>
            <tr>
              <Th>Staff member</Th>
              <Th>Role</Th>
              <Th>Caseload</Th>
              <Th>Visits this week</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {STAFF_WORKLOAD.map((staff) => (
              <tr key={staff.name}>
                <Td>
                  <div className="flex items-center gap-3">
                    <Avatar name={staff.name} size="sm" />
                    <span className="font-semibold text-slate-900">{staff.name}</span>
                  </div>
                </Td>
                <Td>
                  <span className="text-slate-600">{staff.role}</span>
                </Td>
                <Td>
                  <span className="font-medium text-slate-800">{staff.caseload}</span>
                </Td>
                <Td>
                  <span className="font-medium text-slate-800">{staff.visits}</span>
                </Td>
                <Td>
                  <StatusChip tone={staff.tone as any}>{staff.status}</StatusChip>
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      </section>
    </div>
  );
}
