import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
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

export default async function BenefitsNavigatorPage() {
  const session = await requireAuthenticatedSession("/dashboard/benefits-navigator");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

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
      <ErrorState description="Benefits Navigator is disabled until BENEFITS_NAVIGATOR_GLOBAL_ENABLED and organisation settings are approved." />
    );
  }

  const recommended = (tenantDash.recommended ?? []) as Record<string, unknown>[];

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Benefits Navigator (add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Official eligibility is never decided here. Only administrator-verified benefits are shown when active.
        </p>
      </header>
      {admin ? (
        <section className="grid gap-4 sm:grid-cols-4">
          <Stat label="Active benefits" value={String(stats.active_benefits ?? "0")} />
          <Stat label="Assessments" value={String(stats.assessments_total ?? "0")} />
          <Stat label="Saved guidance" value={String(stats.saved_guidance_total ?? "0")} />
          <Stat label="Sources pending" value={String(stats.sources_pending_verification ?? "0")} />
        </section>
      ) : null}
      {tenant ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="font-medium text-slate-800">Recommended for you</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {recommended.length === 0 ? (
              <li className="py-2 text-slate-500">No active benefits configured yet.</li>
            ) : (
              recommended.map((b) => (
                <li key={String(b.id)} className="py-2">
                  {String(b.benefit_name)}
                </li>
              ))
            )}
          </ul>
        </section>
      ) : null}
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="font-medium text-slate-800">Active directory</h2>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {results.length === 0 ? (
            <li className="py-2 text-slate-500">No active benefits match filters.</li>
          ) : (
            results.map((b) => (
              <li key={String(b.id)} className="flex justify-between py-2">
                <span>{String(b.benefit_name)}</span>
                <span className="text-slate-500">{String(b.category_slug)}</span>
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}
