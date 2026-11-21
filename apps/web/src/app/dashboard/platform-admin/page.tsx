import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader, StatusChip } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchOrgGovernanceDashboard } from "@/lib/platformGovernanceApi";
import { requireAuthenticatedSession } from "@/lib/session";

const AREAS = [
  { href: "/dashboard/super-admin/organisations", title: "Organisations", description: "Create and review tenant organisations." },
  { href: "/dashboard/approvals/registrations", title: "Registration approvals", description: "Review new accounts before they can sign in." },
  { href: "/dashboard/governance", title: "Governance", description: "Compliance tasks, privacy requests and system health." },
  { href: "/dashboard/audit", title: "Audit logs", description: "Sensitive actions, who did them and when." },
  { href: "/dashboard/integrations", title: "Integrations", description: "Connections stay off until a provider is authorised." },
  { href: "/dashboard/ai-feature-flags", title: "AI feature flags", description: "Turn organisation AI features on or off." },
];

export default async function PlatformAdminPage() {
  const session = await requireAuthenticatedSession("/dashboard/platform-admin");
  if (session.authorization?.active_role !== "super_admin") {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to open platform admin." />;
  }

  let health: Record<string, unknown> | null = null;
  if (isAuth0Configured() && auth0) {
    try {
      const token = (await auth0.getAccessToken())?.token;
      if (token) {
        const dash = await fetchOrgGovernanceDashboard({
          accessToken: token,
          organisationId: orgId,
          role: session.authorization?.active_role,
        });
        health = (dash.system_health ?? {}) as Record<string, unknown>;
      }
    } catch {
      health = null;
    }
  }

  const checks = [
    { label: "API", value: health?.api_status },
    { label: "Database", value: health?.database_status },
    { label: "Background jobs", value: health?.background_jobs_status },
  ].filter((item) => item.value != null && item.value !== "");

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Platform / Platform admin"
        title="Platform admin"
        description="Global configuration for all organisations."
      />
      <div className="grid items-start gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <Card>
          <nav aria-label="Platform areas" className="space-y-1">
            {AREAS.map((area) => (
              <Link
                key={area.href}
                href={area.href}
                className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                {area.title}
              </Link>
            ))}
          </nav>
        </Card>
        <div className="space-y-4">
          <Card>
            <CardHeader title="Areas" description="Open the live record for each setting. This page does not store a separate configuration." />
            <ul className="divide-y divide-slate-100">
              {AREAS.map((area) => (
                <li key={area.href} className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
                  <div>
                    <Link href={area.href} className="font-semibold text-slate-900 hover:text-brand-700 hover:underline">
                      {area.title}
                    </Link>
                    <p className="mt-0.5 text-sm text-slate-500">{area.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
          {checks.length > 0 ? (
            <Card>
              <CardHeader title="Environment" description="Live checks from the governance record." />
              <ul className="divide-y divide-slate-100">
                {checks.map((item) => (
                  <li key={item.label} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                    <span className="text-sm font-medium text-slate-800">{item.label}</span>
                    <StatusChip status={String(item.value)} />
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
