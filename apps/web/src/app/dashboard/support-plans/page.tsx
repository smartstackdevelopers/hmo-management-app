import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { FilterTabs, humanize, linkClass, StatCard, StatGrid } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { fetchSupportPlansDashboard } from "@/lib/supportPlansApi";
import { requireAuthenticatedSession } from "@/lib/session";

const PLAN_STATUSES = ["draft", "active", "under_review", "on_hold", "completed", "closed"] as const;

const CARDS: { label: string; key: string; tone?: "green" | "amber" | "red" | "blue" | "gray" }[] = [
  { label: "Total plans", key: "total_plans" },
  { label: "Active plans", key: "active_plans", tone: "green" },
  { label: "Under review", key: "plans_under_review", tone: "amber" },
  { label: "On hold", key: "plans_on_hold" },
  { label: "Goals in progress", key: "goals_in_progress", tone: "blue" },
  { label: "Achieved goals", key: "goals_achieved", tone: "green" },
  { label: "Goals at risk", key: "goals_at_risk", tone: "red" },
  { label: "Pending milestones", key: "pending_milestones", tone: "amber" },
  { label: "Overdue milestones", key: "overdue_milestones", tone: "red" },
  { label: "Upcoming reviews", key: "upcoming_reviews", tone: "blue" },
  { label: "Overdue reviews", key: "overdue_reviews", tone: "red" },
];

export default async function SupportPlansDashboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ status?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
  const status = PLAN_STATUSES.includes(params.status as (typeof PLAN_STATUSES)[number]) ? params.status : "";
  const session = await requireAuthenticatedSession("/dashboard/support-plans");
  const permissions = session.authorization?.permissions;
  const role = session.authorization?.active_role;

  if (
    !canAny(permissions, ["support_plans.read", "support_plans.manage"]) ||
    (role !== "organisation_admin" && role !== "support_worker" && role !== "super_admin")
  ) {
    return (
      <EmptyState
        title="Support plans aren't available"
        description="This view is for organisation admins and support workers who can read support plans."
      />
    );
  }

  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in." />;
  }

  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Support plans will be available once sign-in is configured." />;
  }

  let dashboard: Record<string, unknown> | null = null;
  let loadError: string | null = null;
  try {
    const tokenResult = await auth0.getAccessToken();
    const token = tokenResult?.token;
    if (!token) {
      loadError = "We couldn't confirm your sign-in. Please sign in again.";
    } else {
      dashboard = await fetchSupportPlansDashboard({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization?.active_role,
        planStatus: status || undefined,
      });
    }
  } catch (e) {
    loadError = e instanceof Error ? e.message : "We couldn't load support plans. Please try again.";
  }

  if (loadError) {
    return <ErrorState description={loadError} retryHref="/dashboard/support-plans" />;
  }

  const num = (key: string) => (typeof dashboard?.[key] === "number" ? (dashboard[key] as number) : "—");

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Records"
        title="Support plans"
        description="Counts come from your organisation. Support workers only see plans on their caseload."
      />
      <FilterTabs
        tabs={[
          { label: "All", href: "/dashboard/support-plans", active: !status },
          ...PLAN_STATUSES.map((item) => ({
            label: humanize(item),
            href: `/dashboard/support-plans?status=${item}`,
            active: status === item,
          })),
        ]}
      />
      <StatGrid>
        {CARDS.map((card) => (
          <StatCard key={card.key} label={card.label} value={num(card.key)} tone={card.tone} />
        ))}
      </StatGrid>
      <p className="text-sm text-slate-600">
        Open a person from the{" "}
        <Link href="/dashboard/support-worker" className={linkClass}>
          caseload
        </Link>{" "}
        to work on their plan.
      </p>
    </div>
  );
}
