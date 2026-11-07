import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { SupportPlanDraftPanel } from "@/components/support-plans/SupportPlanDraftPanel";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { canRunSupportPlanDraft } from "@/lib/supportPlanDraftView";
import { fetchTenantSupportPlans, type SupportPlanListItem } from "@/lib/supportPlansApi";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function TenantSupportPlansListPage({
  searchParams,
}: {
  searchParams: Promise<{ tenantId?: string }>;
}) {
  const { tenantId } = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/support-plans/tenant");
  const permissions = session.authorization?.permissions;

  if (!canAny(permissions, ["support_plans.read", "support_plans.manage"])) {
    return (
      <EmptyState title="Access denied" description="Requires support plan read permission on the API." />
    );
  }

  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }

  if (!tenantId) {
    return (
      <EmptyState
        title="Tenant required"
        description="Add ?tenantId=… to the URL (UUID from the tenants list)."
      />
    );
  }

  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState title="Auth0 not configured" description="Set Auth0 environment variables for this app." />
    );
  }

  try {
    const tokenResult = await auth0.getAccessToken();
    const token = tokenResult?.token;
    if (!token) {
      return <ErrorState description="Access token unavailable." />;
    }
    const page = await fetchTenantSupportPlans({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      tenantId,
      page: 1,
      pageSize: 50,
    });

    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="Tenant"
          title="Support plans"
          description="Listing is API-authorised; statuses update when plans are activated or closed."
        />
        <Link href="/dashboard/support-plans" className="text-sm text-teal-800 underline">
          ← Progress dashboard
        </Link>
        {page.items.length === 0 ? (
          <p className="text-sm text-slate-600">No support plans for this tenant yet.</p>
        ) : (
          <ul className="space-y-3">
            {page.items.map((item: SupportPlanListItem & Record<string, unknown>) => (
              <li key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-forest-900">{item.title}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs uppercase text-slate-700">
                    {item.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{item.reference_number}</p>
              </li>
            ))}
          </ul>
        )}
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
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load plans"} />;
  }
}
