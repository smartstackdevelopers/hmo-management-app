import Link from "next/link";
import {
  AttentionCard,
  HomeColumns,
  ModuleTiles,
  plural,
  readSessionAccessToken,
  type AttentionEntry,
} from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { StatCard, StatGrid, btnPrimary, btnSecondary } from "@/components/ui/primitives";
import { fetchWorkload, type WorkloadResponse } from "@/lib/incidentsApi";
import { fetchTasks, fetchVisits, type TaskItem, type Visit } from "@/lib/opsApi";
import { canAny } from "@/lib/rbac";
import { fetchSupportPlansDashboard } from "@/lib/supportPlansApi";
import { fetchCaseload, fetchHandovers, type Handover } from "@/lib/supportApi";
import { requireDashboardRole } from "@/lib/session";
import { CaseloadClient } from "@/components/support/CaseloadClient";

const UK_TIME_ZONE = "Europe/London";

function londonDay(date: Date): string {
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: UK_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function whenLabel(iso: string | null | undefined): string | undefined {
  if (!iso) return undefined;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return undefined;
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: UK_TIME_ZONE,
  }).format(date);
}

function numberField(source: Record<string, unknown> | null, key: string): number | null {
  const value = source?.[key];
  return typeof value === "number" ? value : null;
}

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

  const { permissions, active_role: role } = session.authorization;
  const homeSession = { permissions, role };
  const token = await readSessionAccessToken();

  let caseloadError: string | null = null;
  let items: Awaited<ReturnType<typeof fetchCaseload>>["items"] = [];
  let total = 0;
  let workload: WorkloadResponse | null = null;
  let upcomingVisits: { items: Visit[]; total: number } | null = null;
  let overdueTasks: { items: TaskItem[]; total: number } | null = null;
  let handovers: { items: Handover[]; total: number } | null = null;
  let plans: Record<string, unknown> | null = null;

  if (!token) {
    caseloadError = "Please sign in again to load your caseload.";
  } else {
    const opts = { accessToken: token, organisationId: orgId, role };
    const canVisits = canAny(permissions, ["visits.manage.assigned", "tenants.manage"]);
    const canTasks = canAny(permissions, ["tasks.manage.assigned", "tenants.manage"]);
    const canHandovers = canAny(permissions, ["support_notes.read.assigned", "tenants.manage"]);
    const canPlans = canAny(permissions, ["support_plans.read", "support_plans.manage"]);
    const canWorkload = canAny(permissions, ["workload.read", "workload.read.own"]);

    const [caseloadResult, workloadResult, visitsResult, tasksResult, handoversResult, plansResult] =
      await Promise.all([
        fetchCaseload({ ...opts, q: params.q }).then(
          (page) => ({ ok: true as const, page }),
          (error: unknown) => ({ ok: false as const, error }),
        ),
        canWorkload ? fetchWorkload(opts).catch(() => null) : null,
        canVisits ? fetchVisits({ ...opts, upcomingOnly: true }).catch(() => null) : null,
        canTasks ? fetchTasks({ ...opts, overdueOnly: true }).catch(() => null) : null,
        canHandovers ? fetchHandovers({ ...opts, pendingOnly: true }).catch(() => null) : null,
        canPlans ? fetchSupportPlansDashboard(opts).catch(() => null) : null,
      ]);

    if (caseloadResult.ok) {
      items = caseloadResult.page.items;
      total = caseloadResult.page.total;
    } else {
      caseloadError =
        caseloadResult.error instanceof Error ? caseloadResult.error.message : "Failed to load caseload.";
    }
    workload = workloadResult;
    upcomingVisits = visitsResult;
    overdueTasks = tasksResult;
    handovers = handoversResult;
    plans = plansResult;
  }

  const mine = workload?.staff[0] ?? null;
  const visitsToday =
    upcomingVisits && upcomingVisits.items.length >= upcomingVisits.total
      ? upcomingVisits.items.filter((visit) => londonDay(new Date(visit.scheduled_at)) === londonDay(new Date())).length
      : null;
  const overdueTaskCount = mine?.overdue_tasks ?? overdueTasks?.total ?? null;
  const openTaskCount = mine?.open_tasks ?? null;
  const plansToReview = numberField(plans, "upcoming_reviews");
  const overdueReviews = numberField(plans, "overdue_reviews");

  const attention: AttentionEntry[] = [];
  for (const task of overdueTasks?.items.slice(0, 3) ?? []) {
    attention.push({
      key: `task-${task.id}`,
      title: task.title,
      meta: whenLabel(task.due_at) ?? "Overdue",
      tone: "red",
      href: "/dashboard/tasks",
    });
  }
  if ((overdueTasks?.total ?? 0) > (overdueTasks?.items.length ?? 0) && overdueTaskCount) {
    attention.push({
      key: "tasks-more",
      title: plural(overdueTaskCount, "overdue task"),
      tone: "red",
      href: "/dashboard/tasks",
    });
  }
  for (const visit of (upcomingVisits?.items ?? []).filter(
    (visit) => londonDay(new Date(visit.scheduled_at)) === londonDay(new Date()),
  ).slice(0, 2)) {
    attention.push({
      key: `visit-${visit.id}`,
      title: visit.purpose || "Visit today",
      meta: whenLabel(visit.scheduled_at),
      tone: "blue",
      href: "/dashboard/visits",
    });
  }
  for (const handover of handovers?.items.slice(0, 2) ?? []) {
    attention.push({
      key: `handover-${handover.id}`,
      title: handover.summary,
      meta: `${humanizePriority(handover.priority)} · waiting`,
      tone: handover.priority === "high" || handover.priority === "urgent" ? "red" : "amber",
      href: `/dashboard/handovers/${handover.id}`,
    });
  }
  if (overdueReviews) {
    attention.push({
      key: "plans-overdue",
      title: plural(overdueReviews, "support plan review") + " overdue",
      tone: "amber",
      href: "/dashboard/support-plans",
    });
  }

  const title = "My caseload";
  const summary: string[] = [];
  if (title !== "My caseload") summary.push("My caseload");
  if (!caseloadError) summary.push(plural(total, "assigned tenant"));
  if (visitsToday !== null) summary.push(`${plural(visitsToday, "visit")} today`);

  const showCaseload = !caseloadError && (items.length > 0 || Boolean(params.q));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Support Worker"
        title={title}
        description={summary.join(" · ") || "Assigned tenants, visits and follow-ups."}
        actions={
          <>
            <Link href="/dashboard/handovers" className={btnSecondary}>
              Handover
            </Link>
            <Link href="/dashboard/daily-logs/new" className={btnPrimary}>
              Daily log
            </Link>
          </>
        }
      />

      {!caseloadError ? (
        <StatGrid>
          <StatCard label="Assigned tenants" value={total} href="/dashboard/support-worker" />
          {visitsToday !== null ? (
            <StatCard
              label="Visits today"
              value={visitsToday}
              tone={visitsToday > 0 ? "blue" : "gray"}
              href="/dashboard/visits"
            />
          ) : upcomingVisits ? (
            <StatCard label="Upcoming visits" value={upcomingVisits.total} tone="blue" href="/dashboard/visits" />
          ) : null}
          {openTaskCount !== null ? (
            <StatCard
              label="Tasks due"
              value={openTaskCount}
              tone={overdueTaskCount ? "red" : openTaskCount > 0 ? "amber" : "gray"}
              hint={overdueTaskCount ? `${overdueTaskCount} overdue` : openTaskCount > 0 ? "Open" : undefined}
              href="/dashboard/tasks"
            />
          ) : overdueTaskCount !== null ? (
            <StatCard
              label="Overdue tasks"
              value={overdueTaskCount}
              tone={overdueTaskCount > 0 ? "red" : "gray"}
              hint={overdueTaskCount > 0 ? "Action" : undefined}
              href="/dashboard/tasks"
            />
          ) : null}
          {plansToReview !== null ? (
            <StatCard
              label="Plans to review"
              value={plansToReview}
              tone={overdueReviews ? "amber" : "gray"}
              hint={overdueReviews ? `${overdueReviews} overdue` : undefined}
              href="/dashboard/support-plans"
            />
          ) : null}
        </StatGrid>
      ) : null}

      <HomeColumns
        main={
          <div className="space-y-4">
            {caseloadError ? <ErrorState description={caseloadError} retryHref="/dashboard/support-worker" /> : null}
            {!caseloadError && items.length === 0 && !params.q ? (
              <EmptyState
                title="No assigned tenants"
                description="Ask an Organisation Admin to create a case assignment for you."
              />
            ) : null}
            {showCaseload ? (
              <CaseloadClient initialItems={items} total={total} initialQuery={params.q ?? ""} />
            ) : null}
          </div>
        }
        aside={<AttentionCard items={attention} title="Today's priorities" emptyText="Nothing needs your attention right now." />}
      />

      <ModuleTiles
        session={homeSession}
        title="Your work"
        ids={[
          "visits",
          "tasks",
          "handovers",
          "rota",
          "workload",
          "support-plans-dashboard",
          "safeguarding",
          "safeguarding-alerts",
          "incidents",
          "case-summaries",
          "notes-analysis",
          "employment-support",
          "benefits-navigator",
          "maintenance",
          "complaints",
          "documents",
          "communications",
          "training",
        ]}
      />
    </div>
  );
}

function humanizePriority(value: string): string {
  const text = value.replace(/[_-]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1) + " priority";
}
