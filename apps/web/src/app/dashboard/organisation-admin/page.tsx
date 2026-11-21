import Link from "next/link";
import {
  AttentionCard,
  HomeColumns,
  ModuleTiles,
  plural,
  readSessionAccessToken,
  todayLabel,
  visibleModuleIds,
  type AttentionEntry,
} from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Card,
  CardHeader,
  StatCard,
  StatGrid,
  StatusChip,
  btnPrimary,
  btnSecondary,
  humanize,
  linkClass,
} from "@/components/ui/primitives";
import { fetchMaintenanceDashboard, type MaintenanceDashboard } from "@/lib/maintenanceApi";
import { fetchOrgWorkflowsDashboard } from "@/lib/orgWorkflowsApi";
import { canAny } from "@/lib/rbac";
import { getSafeguardingDashboard } from "@/lib/safeguardingAlertsApi";
import { requireDashboardRole } from "@/lib/session";
import { fetchHandovers, type Handover } from "@/lib/supportApi";

const MAINTENANCE_READ = [
  "maintenance.manage",
  "maintenance.read.own",
  "maintenance.read.assigned",
  "maintenance.create.own",
  "maintenance.create.assigned",
  "maintenance.read.property",
];
const WORKFLOWS_READ = ["approvals.inbox.read", "organisation.workflows.manage", "organisation.forms.manage"];
const HANDOVERS_READ = ["support_notes.read.assigned", "tenants.manage", "tenants.read"];
const SAFEGUARDING_READ = ["safeguarding_alerts.read", "safeguarding_alerts.manage"];

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
  const homeSession = { permissions, role };
  const visible = visibleModuleIds(homeSession);

  let maintenance: MaintenanceDashboard | null = null;
  let workflows: Record<string, unknown> | null = null;
  let handovers: { items: Handover[]; total: number } | null = null;
  let safeguarding: Record<string, unknown> | null = null;

  if (orgId) {
    const token = await readSessionAccessToken();
    if (token) {
      const opts = { accessToken: token, organisationId: orgId, role };
      [maintenance, workflows, handovers, safeguarding] = await Promise.all([
        canAny(permissions, MAINTENANCE_READ) ? fetchMaintenanceDashboard(opts).catch(() => null) : null,
        canAny(permissions, WORKFLOWS_READ) ? fetchOrgWorkflowsDashboard(opts).catch(() => null) : null,
        canAny(permissions, HANDOVERS_READ)
          ? fetchHandovers({ ...opts, pendingOnly: true }).catch(() => null)
          : null,
        canAny(permissions, SAFEGUARDING_READ) ? getSafeguardingDashboard(token, orgId).catch(() => null) : null,
      ]);
    }
  }

  const pendingApprovals = numberField(workflows, "pending_approvals");
  const overdueApprovals = numberField(workflows, "overdue_approvals");
  const criticalAlerts = numberField(safeguarding, "critical_open");
  const overdueFollowUps = numberField(safeguarding, "overdue_follow_ups");

  const attention: AttentionEntry[] = [];
  if (criticalAlerts) {
    attention.push({
      key: "safeguarding-critical",
      title: plural(criticalAlerts, "critical safeguarding alert"),
      meta: "Open and waiting for review",
      tone: "red",
      href: "/dashboard/safeguarding-alerts",
    });
  }
  if (maintenance?.urgent_and_emergency) {
    attention.push({
      key: "repairs-urgent",
      title: plural(maintenance.urgent_and_emergency, "urgent repair"),
      meta: "Urgent or emergency priority",
      tone: "red",
      href: "/dashboard/maintenance",
    });
  }
  if (overdueApprovals) {
    attention.push({
      key: "approvals-overdue",
      title: plural(overdueApprovals, "overdue approval"),
      meta: "Past the review deadline",
      tone: "red",
      href: "/dashboard/org-workflows/approvals",
    });
  }
  if (overdueFollowUps) {
    attention.push({
      key: "safeguarding-follow-ups",
      title: plural(overdueFollowUps, "safeguarding follow-up") + " overdue",
      tone: "amber",
      href: "/dashboard/safeguarding-alerts",
    });
  }
  if (maintenance?.overdue_scheduled) {
    attention.push({
      key: "repairs-overdue-visits",
      title: plural(maintenance.overdue_scheduled, "repair visit") + " overdue",
      tone: "amber",
      href: "/dashboard/maintenance",
    });
  }
  if (maintenance?.awaiting_approval) {
    attention.push({
      key: "repairs-approval",
      title: plural(maintenance.awaiting_approval, "repair") + " awaiting approval",
      tone: "amber",
      href: "/dashboard/maintenance/pending",
    });
  }

  const hasStats = Boolean(maintenance || pendingApprovals !== null || handovers || criticalAlerts !== null);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Organisation Admin"
        title="Organisation overview"
        description={todayLabel()}
        actions={
          <>
            {visible.has("reports") ? (
              <Link href="/dashboard/reports" className={btnSecondary}>
                Reports
              </Link>
            ) : null}
            {visible.has("case-assignments") ? (
              <Link href="/dashboard/case-assignments" className={btnPrimary}>
                Assign a case
              </Link>
            ) : null}
          </>
        }
      />

      {!orgId ? (
        <EmptyState
          title="Choose an organisation"
          description="Your account isn't linked to an active organisation yet. Ask a Super Admin to add you."
        />
      ) : null}

      {hasStats ? (
        <StatGrid>
          {maintenance ? (
            <StatCard
              label="Open repairs"
              value={maintenance.open_count}
              tone="red"
              hint={maintenance.urgent_and_emergency ? `${maintenance.urgent_and_emergency} urgent` : undefined}
              href="/dashboard/maintenance"
            />
          ) : null}
          {pendingApprovals !== null ? (
            <StatCard
              label="Approvals waiting"
              value={pendingApprovals}
              tone="amber"
              hint={pendingApprovals > 0 ? "Review" : undefined}
              href="/dashboard/org-workflows/approvals"
            />
          ) : null}
          {handovers ? (
            <StatCard label="Pending handovers" value={handovers.total} href="/dashboard/handovers" />
          ) : null}
          {criticalAlerts !== null ? (
            <StatCard
              label="Critical safeguarding alerts"
              value={criticalAlerts}
              tone="red"
              hint={criticalAlerts > 0 ? "Act now" : undefined}
              href="/dashboard/safeguarding-alerts"
            />
          ) : null}
        </StatGrid>
      ) : null}

      <HomeColumns
        main={
          handovers ? (
            <Card>
              <CardHeader
                title="Pending handovers"
                description="Handovers between staff that haven't been completed yet."
                action={
                  <Link href="/dashboard/handovers" className={linkClass}>
                    View all
                  </Link>
                }
              />
              {handovers.items.length === 0 ? (
                <p className="text-sm text-slate-500">No handovers are waiting. Everything has been picked up.</p>
              ) : (
                <ul className="-mx-2 divide-y divide-slate-100">
                  {handovers.items.slice(0, 6).map((item) => (
                    <li key={item.id}>
                      <Link
                        href={`/dashboard/handovers/${item.id}`}
                        className="flex items-center gap-3 rounded-lg px-2 py-2.5 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-semibold text-slate-900">{item.summary}</span>
                          <span className="block text-xs text-slate-500">{humanize(item.priority)} priority</span>
                        </span>
                        <StatusChip status={item.status} />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ) : undefined
        }
        aside={<AttentionCard items={attention} emptyText="Nothing urgent right now. You're all caught up." />}
      />

      <ModuleTiles
        session={homeSession}
        title="Run your organisation"
        ids={[
          "tenants",
          "properties",
          "rooms",
          "case-assignments",
          "handovers",
          "rota",
          "maintenance",
          "complaints",
          "housing-applications",
          "safeguarding-alerts",
          "org-workflows",
          "documents",
          "files",
          "communications",
          "reports",
          "audit",
        ]}
        extra={[
          {
            href: "/dashboard/approvals/registrations",
            title: "Registration requests",
            description: "Approve or decline people asking to join.",
          },
        ]}
      />
    </div>
  );
}
