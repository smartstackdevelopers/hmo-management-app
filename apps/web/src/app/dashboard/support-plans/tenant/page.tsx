import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { SupportPlanDraftPanel } from "@/components/support-plans/SupportPlanDraftPanel";
import { btnSecondary, DataTable, FilterTabs, humanize, inputClass, linkClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { canRunSupportPlanDraft } from "@/lib/supportPlanDraftView";
import { fetchTenantSupportPlans, type SupportPlanListItem } from "@/lib/supportPlansApi";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function TenantSupportPlansListPage({
  searchParams,
}: {
  searchParams: Promise<{ tenantId?: string; q?: string; status?: string }>;
}) {
  const { tenantId, q: rawQuery, status: rawStatus } = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/support-plans/tenant");
  const permissions = session.authorization?.permissions;

  if (!canAny(permissions, ["support_plans.read", "support_plans.manage"])) {
    return (
      <EmptyState title="Support plans aren't available" description="You need permission to read support plans." />
    );
  }

  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in." />;
  }

  if (!tenantId) {
    return (
      <EmptyState
        title="Choose a tenant"
        description="Open this page from a case, or add the tenant reference to the address."
      />
    );
  }

  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState title="Sign-in isn't set up yet" description="Support plans will be available once sign-in is configured." />
    );
  }

  try {
    const tokenResult = await auth0.getAccessToken();
    const token = tokenResult?.token;
    if (!token) {
      return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/support-plans/tenant" />;
    }
    const page = await fetchTenantSupportPlans({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      tenantId,
      page: 1,
      pageSize: 50,
    });
    const q = (rawQuery ?? "").trim();
    const needle = q.toLowerCase();
    const statuses = [...new Set(page.items.map((item) => item.status).filter(Boolean))].sort();
    const status = statuses.includes(rawStatus ?? "") ? rawStatus ?? "" : "";
    const visible = page.items.filter((item) => {
      if (status && item.status !== status) return false;
      if (!needle) return true;
      return item.title.toLowerCase().includes(needle) || item.reference_number.toLowerCase().includes(needle);
    });
    function plansHref(next: { status?: string }) {
      const search = new URLSearchParams();
      search.set("tenantId", tenantId ?? "");
      if (q) search.set("q", q);
      if (next.status) search.set("status", next.status);
      return `/dashboard/support-plans/tenant?${search.toString()}`;
    }

    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Records"
          title="Support plans"
          description="Plans for this tenant. Status changes when a plan is activated or closed."
        />
        <Link href="/dashboard/support-plans" className={linkClass}>
          Progress dashboard
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            <input type="hidden" name="tenantId" value={tenantId} />
            {status ? <input type="hidden" name="status" value={status} /> : null}
            <label className="sr-only" htmlFor="plan-search">
              Search plans
            </label>
            <input id="plan-search" name="q" defaultValue={q} placeholder="Search title or reference" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: plansHref({}), active: !status },
              ...statuses.map((item) => ({
                label: humanize(item),
                href: plansHref({ status: item }),
                active: status === item,
              })),
            ]}
          />
        </div>
        {visible.length === 0 ? (
          <EmptyState
            title="No support plans"
            description={q || status ? "No plans match this search or status." : "Plans created for this tenant will appear here."}
            action={q || status ? { label: "Clear filters", href: `/dashboard/support-plans/tenant?tenantId=${tenantId}` } : undefined}
          />
        ) : (
          <DataTable caption="Support plans">
            <thead>
              <tr>
                <Th>Plan</Th>
                <Th>Reference</Th>
                <Th>Review</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item: SupportPlanListItem) => (
                <tr key={item.id} className="hover:bg-slate-50/60">
                  <Td className="font-semibold text-slate-900">{item.title}</Td>
                  <Td className="font-mono text-xs">{item.reference_number}</Td>
                  <Td>{item.planned_review_date ?? "—"}</Td>
                  <Td>
                    <StatusChip status={item.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <p className="text-sm text-slate-500">
          {visible.length === 0 ? `Showing 0 of ${page.total}` : `Showing 1–${visible.length} of ${page.total}`}
        </p>
        {canRunSupportPlanDraft(permissions) ? (
          <SupportPlanDraftPanel
            tenantId={tenantId}
            planId={page.items[0]?.id ?? null}
            accessToken={token}
            organisationId={orgId}
            role={session.authorization?.active_role}
            permissions={permissions ?? []}
          />
        ) : null}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "We couldn't load support plans. Please try again."}
        retryHref="/dashboard/support-plans/tenant"
      />
    );
  }
}
