import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { fetchSupportPlansDashboard } from "@/lib/supportPlansApi";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function SupportPlansDashboardPage() {
  const session = await requireAuthenticatedSession("/dashboard/support-plans");
  const permissions = session.authorization?.permissions;
  const role = session.authorization?.active_role;

  if (
    !canAny(permissions, ["support_plans.read", "support_plans.manage"]) ||
    (role !== "organisation_admin" && role !== "support_worker" && role !== "super_admin")
  ) {
    return (
      <EmptyState
        title="Access denied"
        description="Support plans dashboard requires organisation admin or support worker with support_plans.read."
      />
    );
  }

  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }

  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load dashboard." />;
  }

  let dashboard: Record<string, unknown> | null = null;
  let loadError: string | null = null;
  try {
    const tokenResult = await auth0.getAccessToken();
    const token = tokenResult?.token;
    if (!token) {
      loadError = "Access token unavailable.";
    } else {
      dashboard = await fetchSupportPlansDashboard({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization?.active_role,
      });
    }
  } catch (e) {
    loadError = e instanceof Error ? e.message : "Unable to load dashboard";
  }

  if (loadError) {
    return <ErrorState description={loadError} />;
  }

  const num = (k: string) => (typeof dashboard?.[k] === "number" ? (dashboard[k] as number) : "—");

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <PageHeader
        eyebrow="F2.10"
        title="Support plans progress"
        description="Counts come from the API and respect organisation isolation and caseload scope for support workers."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { label: "Total plans", key: "total_plans" },
          { label: "Active plans", key: "active_plans" },
          { label: "Under review", key: "plans_under_review" },
          { label: "On hold", key: "plans_on_hold" },
          { label: "Goals in progress", key: "goals_in_progress" },
          { label: "Achieved goals", key: "goals_achieved" },
          { label: "Goals at risk", key: "goals_at_risk" },
          { label: "Pending milestones", key: "pending_milestones" },
          { label: "Overdue milestones", key: "overdue_milestones" },
          { label: "Upcoming reviews", key: "upcoming_reviews" },
          { label: "Overdue reviews", key: "overdue_reviews" },
        ].map((card) => (
          <div key={card.key} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{card.label}</p>
            <p className="mt-2 text-2xl font-semibold text-forest-900">{num(card.key)}</p>
          </div>
        ))}
      </div>

      <p className="text-sm text-slate-600">
        Manage plans from a tenant case: open{" "}
        <Link href="/dashboard/support-worker" className="text-teal-800 underline">
          caseload
        </Link>{" "}
        and use Support plans (when linked), or call the API at{" "}
        <code className="rounded bg-slate-100 px-1">/api/v1/tenants/{"{tenant_id}"}/support-plans</code>.
      </p>
    </div>
  );
}
