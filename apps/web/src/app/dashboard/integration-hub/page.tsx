import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader, DataTable, StatCard, StatGrid, StatusChip, Td, Th } from "@/components/ui/primitives";
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
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;

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
      <ErrorState
        title="Integrations unavailable"
        description="The integration hub isn't switched on for this organisation yet."
        retryHref="/dashboard/integration-hub"
      />
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
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Insights"
        title="Integrations"
        description="Connections are prepared locally. A provider is connected only after a successful connection test."
      />
      {typeof dash.disclaimer === "string" ? (
        <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{dash.disclaimer}</p>
      ) : null}
      <StatGrid>
        {stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} tone={s.label === "Webhook failures" ? "amber" : "gray"} />
        ))}
      </StatGrid>
      <Card padded={false}>
        <div className="p-5 pb-0">
          <CardHeader title="Provider directory" description="Sandbox providers registered for this organisation." />
        </div>
        {providers.length === 0 ? (
          <p className="px-5 pb-5 text-sm text-slate-500">No providers registered.</p>
        ) : (
          <DataTable caption="Integration providers">
            <thead>
              <tr>
                <Th>Provider</Th>
                <Th>Category</Th>
                <Th>Mode</Th>
              </tr>
            </thead>
            <tbody>
              {providers.slice(0, 20).map((p) => (
                <tr key={String(p.provider_key)}>
                  <Td className="font-semibold text-slate-900">{String(p.provider_name)}</Td>
                  <Td>{String(p.category_slug)}</Td>
                  <Td>
                    <StatusChip tone={p.sandbox_only ? "gray" : "blue"}>{p.sandbox_only ? "Sandbox" : "Live"}</StatusChip>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </Card>
      {health.length > 0 ? (
        <DataTable caption="Connection health">
          <thead>
            <tr>
              <Th>Integration</Th>
              <Th>Health</Th>
              <Th>Connection</Th>
            </tr>
          </thead>
          <tbody>
            {health.map((h) => (
              <tr key={String(h.integration_id)}>
                <Td className="font-semibold text-slate-900">{String(h.name)}</Td>
                <Td>
                  <StatusChip status={String(h.health_status)} />
                </Td>
                <Td>
                  <StatusChip status={h.connected_claim ? "connected" : "disabled"}>
                    {h.connected_claim ? "Connected" : "Not connected"}
                  </StatusChip>
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      ) : null}
    </div>
  );
}
