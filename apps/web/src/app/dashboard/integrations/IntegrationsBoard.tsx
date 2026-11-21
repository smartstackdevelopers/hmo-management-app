"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Card,
  CardHeader,
  DataTable,
  StatusChip,
  Td,
  Th,
  btnPrimary,
  btnSecondary,
  humanize,
  inputClass,
  labelClass,
} from "@/components/ui/primitives";
import {
  createIntegration,
  createIntegrationMapping,
  fetchIntegrationActivity,
  fetchIntegrationSyncJobs,
  fetchIntegrations,
  startIntegrationSync,
  testIntegrationConnection,
  updateIntegration,
} from "@/lib/integrationsApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
};

const PROVIDERS = [
  { key: "council_generic", label: "Council" },
  { key: "hr_generic", label: "HR" },
  { key: "finance_generic", label: "Finance" },
  { key: "community_service_generic", label: "Community services" },
];

function friendly(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) return fallback;
  const text = error.message.trim();
  if (!text || text.startsWith("{") || text.startsWith("[") || text.length > 180) return fallback;
  return text;
}

function whenLabel(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/London",
  }).format(date);
}

export function IntegrationsBoard({ accessToken, organisationId, role, canManage }: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [jobs, setJobs] = useState<Record<string, unknown>[]>([]);
  const [activity, setActivity] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [pending, startTransition] = useTransition();
  const [category, setCategory] = useState("all");
  const [name, setName] = useState("");
  const [providerKey, setProviderKey] = useState(PROVIDERS[0]?.key ?? "council_generic");
  const [baseUrl, setBaseUrl] = useState("");
  const [authType, setAuthType] = useState("api_key");
  const [apiKey, setApiKey] = useState("");
  const [clientId, setClientId] = useState("");
  const [mapIntegrationId, setMapIntegrationId] = useState("");
  const [mapSource, setMapSource] = useState("");
  const [mapDest, setMapDest] = useState("");
  const [mapType, setMapType] = useState("string");

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        const [list, syncs, act] = await Promise.all([
          fetchIntegrations(auth),
          fetchIntegrationSyncJobs(auth),
          fetchIntegrationActivity(auth),
        ]);
        setItems(list.items);
        setJobs(syncs.items);
        setActivity(act.items);
        setLoaded(true);
      } catch (loadError) {
        setError(friendly(loadError, "Integrations could not be loaded."));
        setLoaded(true);
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const categories = Array.from(new Set(items.map((item) => String(item.category || "other"))));
  const visible = category === "all" ? items : items.filter((item) => String(item.category || "other") === category);
  const groups = categories
    .map((key) => ({
      key,
      label: humanize(key),
      items: visible.filter((item) => String(item.category || "other") === key),
    }))
    .filter((group) => group.items.length > 0);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Insights / Integrations"
        title="Integrations"
        description="Connections are prepared locally. Paid services stay off until authorised."
        actions={
          <a href="#sync-log" className={btnPrimary}>
            Sync log
          </a>
        }
      />
      {error ? <ErrorState description={error} /> : null}
      {pending && !loaded ? <p className="text-sm text-slate-500">Loading integrations…</p> : null}

      {loaded && items.length === 0 ? (
        <EmptyState
          title="No integrations yet"
          description="Add a connection when a provider has been authorised. Status stays disconnected until a real connection test succeeds."
        />
      ) : null}

      {items.length > 0 ? (
        <div className="grid items-start gap-4 lg:grid-cols-[14rem_minmax(0,1fr)]">
          <Card>
            <nav aria-label="Integration categories" className="space-y-1">
              {[{ key: "all", label: "All" }, ...categories.map((key) => ({ key, label: humanize(key) }))].map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  aria-current={category === tab.key ? "true" : undefined}
                  onClick={() => setCategory(tab.key)}
                  className={`block w-full rounded-lg px-3 py-2 text-left text-sm font-medium ${
                    category === tab.key ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </Card>
          <div className="space-y-4">
            {groups.map((group) => (
              <Card key={group.key}>
                <CardHeader title={group.label} />
                <ul className="divide-y divide-slate-100">
                  {group.items.map((item) => {
                    const enabled = Boolean(item.is_enabled);
                    const status = enabled ? String(item.connection_status || "unknown") : "disabled";
                    return (
                      <li key={String(item.id)} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-900">{String(item.name)}</p>
                          <p className="mt-0.5 text-sm text-slate-500">
                            {String(item.provider_name || humanize(String(item.provider_key || "")))}
                            {item.last_error ? ` — ${String(item.last_error)}` : ""}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusChip status={status} />
                          {canManage ? (
                            <>
                              <button
                                type="button"
                                className={btnSecondary}
                                onClick={() =>
                                  startTransition(async () => {
                                    await updateIntegration(auth, String(item.id), { is_enabled: !enabled });
                                    refresh();
                                  })
                                }
                              >
                                {enabled ? "Disable" : "Enable"}
                              </button>
                              <button
                                type="button"
                                className={btnSecondary}
                                onClick={() =>
                                  startTransition(async () => {
                                    try {
                                      await testIntegrationConnection(auth, String(item.id));
                                      refresh();
                                    } catch (testError) {
                                      setError(friendly(testError, "The connection test failed."));
                                      refresh();
                                    }
                                  })
                                }
                              >
                                Test
                              </button>
                              <button
                                type="button"
                                className={btnSecondary}
                                onClick={() =>
                                  startTransition(async () => {
                                    try {
                                      await startIntegrationSync(auth, String(item.id), "health_check");
                                      refresh();
                                    } catch (syncError) {
                                      setError(friendly(syncError, "The sync could not be started."));
                                      refresh();
                                    }
                                  })
                                }
                              >
                                Sync
                              </button>
                            </>
                          ) : null}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </Card>
            ))}
          </div>
        </div>
      ) : null}

      <p className="text-xs text-slate-500">
        Showing {visible.length === 0 ? "0" : `1–${visible.length}`} of {items.length}
      </p>

      {canManage ? (
        <form
          className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
          onSubmit={(event) => {
            event.preventDefault();
            startTransition(async () => {
              try {
                const credentials: Record<string, string> = {};
                if (authType === "api_key" && apiKey) credentials.api_key = apiKey;
                if (authType === "bearer" && apiKey) credentials.bearer_token = apiKey;
                if (authType === "oauth2" && apiKey) credentials.client_secret = apiKey;
                await createIntegration(auth, {
                  name: name.trim(),
                  provider_key: providerKey,
                  api_base_url: baseUrl || null,
                  auth_type: authType,
                  config: authType === "oauth2" && clientId ? { oauth_client_id: clientId } : {},
                  credentials,
                  is_enabled: true,
                });
                setName("");
                setBaseUrl("");
                setApiKey("");
                setClientId("");
                refresh();
              } catch (createError) {
                setError(friendly(createError, "The integration could not be saved."));
              }
            });
          }}
        >
          <h2 className="text-base font-semibold text-slate-900">Add integration</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="integration-name">
                Name
              </label>
              <input id="integration-name" className={inputClass} value={name} onChange={(event) => setName(event.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="integration-provider">
                Provider
              </label>
              <select id="integration-provider" className={inputClass} value={providerKey} onChange={(event) => setProviderKey(event.target.value)}>
                {PROVIDERS.map((provider) => (
                  <option key={provider.key} value={provider.key}>
                    {provider.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="integration-url">
                API base URL
              </label>
              <input id="integration-url" className={inputClass} value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://" />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="integration-auth">
                Authentication
              </label>
              <select id="integration-auth" className={inputClass} value={authType} onChange={(event) => setAuthType(event.target.value)}>
                <option value="api_key">API key</option>
                <option value="bearer">Bearer token</option>
                <option value="oauth2">OAuth</option>
                <option value="none">None</option>
              </select>
            </div>
            {authType === "oauth2" ? (
              <div className="space-y-1.5">
                <label className={labelClass} htmlFor="integration-client">
                  Client id
                </label>
                <input id="integration-client" className={inputClass} value={clientId} onChange={(event) => setClientId(event.target.value)} />
              </div>
            ) : null}
            {authType !== "none" ? (
              <div className="space-y-1.5 md:col-span-2">
                <label className={labelClass} htmlFor="integration-secret">
                  Secret
                </label>
                <input id="integration-secret" type="password" autoComplete="off" className={inputClass} value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
              </div>
            ) : null}
          </div>
          <button type="submit" className={btnPrimary} disabled={pending}>
            Save integration
          </button>
        </form>
      ) : null}

      <section id="sync-log" className="space-y-3">
        <h2 className="text-base font-semibold text-slate-900">Sync log</h2>
        {jobs.length === 0 ? (
          <EmptyState title="No sync jobs yet" description="A job appears here after a connection is tested or a sync is started." />
        ) : (
          <DataTable caption="Sync jobs">
            <thead>
              <tr>
                <Th>Status</Th>
                <Th>Direction</Th>
                <Th>Succeeded</Th>
                <Th>Failed</Th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={String(job.id)}>
                  <Td>
                    <StatusChip status={String(job.status ?? "")} />
                  </Td>
                  <Td>{humanize(String(job.direction ?? ""))}</Td>
                  <Td>{String(job.success_count ?? 0)}</Td>
                  <Td>{String(job.failure_count ?? 0)}</Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <p className="text-xs text-slate-500">
          Showing {jobs.length === 0 ? "0" : `1–${jobs.length}`} of {jobs.length}
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-slate-900">Activity</h2>
        {activity.length === 0 ? (
          <EmptyState title="No activity yet" description="Connection tests and syncs will be listed here." />
        ) : (
          <DataTable caption="Integration activity">
            <thead>
              <tr>
                <Th>Action</Th>
                <Th>Summary</Th>
                <Th>When</Th>
                <Th>Result</Th>
              </tr>
            </thead>
            <tbody>
              {activity.map((row) => (
                <tr key={String(row.id)}>
                  <Td className="font-semibold text-slate-900">{humanize(String(row.action ?? ""))}</Td>
                  <Td>{String(row.summary || "—")}</Td>
                  <Td className="whitespace-nowrap text-slate-500">{whenLabel(row.created_at)}</Td>
                  <Td>
                    <StatusChip status={String(row.outcome ?? "")} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </section>

      {canManage && items.length > 0 ? (
        <form
          className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
          onSubmit={(event) => {
            event.preventDefault();
            if (!mapIntegrationId) return;
            startTransition(async () => {
              try {
                await createIntegrationMapping(auth, mapIntegrationId, {
                  name: "default",
                  mappings: [
                    {
                      source_field: mapSource.trim(),
                      destination_field: mapDest.trim(),
                      data_type: mapType,
                      required: false,
                    },
                  ],
                });
                setMapSource("");
                setMapDest("");
                refresh();
              } catch (mapError) {
                setError(friendly(mapError, "The field mapping could not be saved."));
              }
            });
          }}
        >
          <h2 className="text-base font-semibold text-slate-900">Field mapping</h2>
          <p className="text-sm text-slate-500">Map partner fields explicitly. Import still needs a successful connection test.</p>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="map-integration">
                Integration
              </label>
              <select id="map-integration" className={inputClass} value={mapIntegrationId} onChange={(event) => setMapIntegrationId(event.target.value)} required>
                <option value="">Choose an integration</option>
                {items.map((item) => (
                  <option key={String(item.id)} value={String(item.id)}>
                    {String(item.name)}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="map-type">
                Data type
              </label>
              <select id="map-type" className={inputClass} value={mapType} onChange={(event) => setMapType(event.target.value)}>
                {["string", "integer", "number", "boolean", "date", "datetime"].map((type) => (
                  <option key={type} value={type}>
                    {humanize(type)}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="map-source">
                Source field
              </label>
              <input id="map-source" className={inputClass} value={mapSource} onChange={(event) => setMapSource(event.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="map-dest">
                Destination field
              </label>
              <input id="map-dest" className={inputClass} value={mapDest} onChange={(event) => setMapDest(event.target.value)} required />
            </div>
          </div>
          <button type="submit" className={btnPrimary} disabled={pending}>
            Save mapping
          </button>
        </form>
      ) : null}
    </div>
  );
}
