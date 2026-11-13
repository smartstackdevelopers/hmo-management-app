import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { fetchHubHealth, fetchHubProviders, fetchIntegrationHubDashboard } from "@/lib/integrationHubApi";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = [
  "integration_hub.read",
  "integration_hub.manage",
  "integration_hub.reports",
  "integrations.read",
  "integrations.manage",
];

export default async function IntegrationHubPage() {
  const session = await requireAuthenticatedSession("/dashboard/integration-hub");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  const auth = { accessToken: token, organisationId: orgId, role: session.authorization?.active_role };

  let dash: Record<string, unknown> = {};
  let providers: Record<string, unknown>[] = [];
  let health: Record<string, unknown>[] = [];

  try {
    dash = await fetchIntegrationHubDashboard(auth);
    providers = await fetchHubProviders(auth);
    if (session.authorization?.permissions?.includes("integration_hub.reports")) {
      health = await fetchHubHealth(auth);
    }
  } catch {
    return (
      <ErrorState description="Deep Integration Hub is disabled until INTEGRATION_HUB_GLOBAL_ENABLED and organisation settings are approved." />
    );
  }

  const stats = [
    { label: "Total integrations", value: String(dash.total_integrations ?? "0") },
    { label: "Active", value: String(dash.active_integrations ?? "0") },
    { label: "Connected", value: String(dash.connected_integrations ?? "0") },
    { label: "Webhook failures", value: String(dash.webhook_failures ?? "0") },
    { label: "API calls (1h)", value: String(dash.api_calls_last_hour ?? "0") },
    { label: "Module bindings", value: String(dash.active_module_bindings ?? "0") },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Integration Hub (F8.9 add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Extends the F6.4 integration foundation. Providers show as connected only after a successful connection test.
        </p>
        {typeof dash.disclaimer === "string" ? <p className="mt-2 text-xs text-amber-800">{dash.disclaimer}</p> : null}
      </header>
      <section className="grid gap-4 sm:grid-cols-3">
        {stats.map((s) => (
          <div key={s.label} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs uppercase tracking-wide text-slate-500">{s.label}</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{s.value}</div>
          </div>
        ))}
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="font-medium text-slate-800">Provider directory (sandbox)</h2>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {providers.length === 0 ? (
            <li className="py-2 text-slate-500">No providers registered.</li>
          ) : (
            providers.slice(0, 20).map((p) => (
              <li key={String(p.provider_key)} className="flex justify-between py-2">
                <span>
                  {String(p.provider_name)} <span className="text-slate-400">({String(p.category_slug)})</span>
                </span>
                {p.sandbox_only ? <span className="text-xs text-slate-500">sandbox</span> : null}
              </li>
            ))
          )}
        </ul>
      </section>
      {health.length > 0 ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="font-medium text-slate-800">Connection health</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {health.map((h) => (
              <li key={String(h.integration_id)} className="flex justify-between py-2">
                <span>{String(h.name)}</span>
                <span className="text-slate-500">
                  {String(h.health_status)} / {h.connected_claim ? "connected" : "not connected"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
