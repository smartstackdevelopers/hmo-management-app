import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader, DataTable, StatCard, StatGrid, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import {
  getBenefitsNavigatorReports,
  getTenantBenefitsDashboard,
  searchBenefits,
} from "@/lib/benefitsNavigatorApi";

const READ = [
  "benefits_navigator.read",
  "benefits_navigator.manage",
  "benefits_navigator.tenant",
  "benefits_navigator.staff.assist",
];

function text(value: unknown): string {
  return value == null || value === "" ? "—" : String(value);
}

export default async function BenefitsNavigatorPage() {
  const session = await requireAuthenticatedSession("/dashboard/benefits-navigator");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/benefits-navigator" />;

  const perms = session.authorization?.permissions ?? [];
  const admin = perms.includes("benefits_navigator.manage") || perms.includes("benefits_navigator.reports");
  const tenant = perms.includes("benefits_navigator.tenant");

  let stats: Record<string, unknown> = {};
  let tenantDash: Record<string, unknown> = {};
  let results: Record<string, unknown>[] = [];

  try {
    if (admin) stats = await getBenefitsNavigatorReports(token, orgId);
    if (tenant) tenantDash = await getTenantBenefitsDashboard(token, orgId);
    results = await searchBenefits(token, orgId);
  } catch {
    return (
      <ErrorState description="Benefits Navigator stays off until the organisation turns the add-on on." retryHref="/dashboard/benefits-navigator" />
    );
  }

  const recommended = (tenantDash.recommended ?? []) as Record<string, unknown>[];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Community"
        title="Benefits navigator"
        description="This does not decide official eligibility. Only administrator-verified benefits are shown when they are active."
      />
      {admin ? (
        <StatGrid>
          <StatCard label="Active benefits" value={text(stats.active_benefits ?? 0)} />
          <StatCard label="Assessments" value={text(stats.assessments_total ?? 0)} />
          <StatCard label="Saved guidance" value={text(stats.saved_guidance_total ?? 0)} />
          <StatCard label="Sources pending" value={text(stats.sources_pending_verification ?? 0)} tone="amber" />
        </StatGrid>
      ) : null}
      {tenant ? (
        <Card>
          <CardHeader title="Recommended for you" description="Based on active, verified benefits in this organisation." />
          {recommended.length === 0 ? (
            <p className="text-sm text-slate-500">No active benefits configured yet.</p>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {recommended.map((benefit) => (
                <li key={text(benefit.id)} className="py-2.5 font-semibold text-slate-900">
                  {text(benefit.benefit_name)}
                </li>
              ))}
            </ul>
          )}
        </Card>
      ) : null}
      {results.length === 0 ? (
        <EmptyState title="No active benefits" description="Verified benefits will appear in the directory when they are active." />
      ) : (
        <DataTable caption="Active benefits">
          <thead>
            <tr>
              <Th>Benefit</Th>
              <Th>Category</Th>
            </tr>
          </thead>
          <tbody>
            {results.map((benefit) => (
              <tr key={text(benefit.id)} className="hover:bg-slate-50/60">
                <Td className="font-semibold text-slate-900">{text(benefit.benefit_name)}</Td>
                <Td>{text(benefit.category_slug).replaceAll("_", " ")}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}
