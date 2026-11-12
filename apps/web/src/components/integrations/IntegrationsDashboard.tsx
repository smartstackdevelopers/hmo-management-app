"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  createIntegration,
  fetchIntegrationActivity,
  fetchIntegrationSyncJobs,
  fetchIntegrations,
  fetchIntegrationsDashboard,
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
  { key: "council_generic", label: "Council API (generic)" },
  { key: "hr_generic", label: "HR API (generic)" },
  { key: "finance_generic", label: "Finance API (generic)" },
  { key: "community_service_generic", label: "Community services API (generic)" },
];

export function IntegrationsDashboard({ accessToken, organisationId, role, canManage }: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [jobs, setJobs] = useState<Record<string, unknown>[]>([]);
  const [activity, setActivity] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [category, setCategory] = useState("");

  const [name, setName] = useState("Council foundation connector");
  const [providerKey, setProviderKey] = useState("council_generic");
  const [baseUrl, setBaseUrl] = useState("");
  const [authType, setAuthType] = useState("api_key");
  const [apiKey, setApiKey] = useState("");

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        const [d, list, syncs, act] = await Promise.all([
          fetchIntegrationsDashboard(auth),
          fetchIntegrations({ ...auth, category: category || undefined }),
          fetchIntegrationSyncJobs(auth),
          fetchIntegrationActivity(auth),
        ]);
        setDash(d);
        setItems(list.items);
        setJobs(syncs.items);
        setActivity(act.items);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load integrations");
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const cards = [
    { label: "Total", value: dash?.total_integrations },
    { label: "Active", value: dash?.active_integrations },
    { label: "Disabled", value: dash?.disabled_integrations },
    { label: "Connected", value: dash?.connected_integrations },
    { label: "Failed connections", value: dash?.failed_connections },
    { label: "Failed syncs", value: dash?.failed_sync_jobs },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Integration hub</h1>
        <p className="mt-1 text-sm text-slate-600">
          Secure foundation for future Council, HR, Finance and community service APIs. Connected status
          appears only after a real successful connection test — never mock production status.
        </p>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {pending && !dash ? <p className="text-sm text-slate-500">Loading…</p> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <div key={c.label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-slate-500">{c.label}</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{String(c.value ?? "—")}</div>
          </div>
        ))}
      </div>

      {canManage ? (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-medium text-slate-800">Add integration</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-sm">
              Name
              <input className="mt-1 w-full rounded border px-2 py-1.5" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="text-sm">
              Provider
              <select
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={providerKey}
                onChange={(e) => setProviderKey(e.target.value)}
              >
                {PROVIDERS.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              API base URL (https)
              <input
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://partner.example/api"
              />
            </label>
            <label className="text-sm">
              Auth type
              <select
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={authType}
                onChange={(e) => setAuthType(e.target.value)}
              >
                <option value="api_key">api_key</option>
                <option value="bearer">bearer</option>
                <option value="oauth2">oauth2</option>
                <option value="none">none</option>
              </select>
            </label>
            <label className="text-sm md:col-span-2">
              API key / token (stored encrypted; never returned by API)
              <input
                type="password"
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                autoComplete="off"
              />
            </label>
          </div>
          <button
            type="button"
            disabled={pending}
            className="rounded bg-teal-800 px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
            onClick={() =>
              startTransition(async () => {
                try {
                  const credentials: Record<string, string> = {};
                  if (authType === "api_key" && apiKey) credentials.api_key = apiKey;
                  if (authType === "bearer" && apiKey) credentials.bearer_token = apiKey;
                  if (authType === "oauth2" && apiKey) credentials.client_secret = apiKey;
                  await createIntegration(auth, {
                    name,
                    provider_key: providerKey,
                    api_base_url: baseUrl || null,
                    auth_type: authType,
                    config: authType === "oauth2" ? { oauth_client_id: "configure-me" } : {},
                    credentials,
                    is_enabled: true,
                  });
                  setApiKey("");
                  refresh();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Create failed");
                }
              })
            }
          >
            Create integration
          </button>
        </div>
      ) : null}

      <div className="flex gap-2">
        <select className="rounded border px-2 py-1.5 text-sm" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          <option value="council">council</option>
          <option value="hr">hr</option>
          <option value="finance">finance</option>
          <option value="community_service">community_service</option>
        </select>
        <button type="button" className="rounded border px-3 py-1.5 text-sm" onClick={refresh}>
          Refresh
        </button>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Integrations</h2>
        {!items.length ? (
          <p className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
            No integrations configured yet.
          </p>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={String(item.id)} className="rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-900">{String(item.name)}</div>
                    <div className="text-slate-600">
                      {String(item.provider_name)} · {String(item.category)} · {String(item.connection_status)} ·{" "}
                      health {String(item.health_status)} · {item.is_enabled ? "enabled" : "disabled"}
                    </div>
                    <div className="text-xs text-slate-500">
                      last check {String(item.last_connection_check_at ?? "—")} · last sync{" "}
                      {String(item.last_successful_sync_at ?? "—")}
                      {item.last_error ? ` · error: ${String(item.last_error)}` : ""}
                    </div>
                  </div>
                  {canManage ? (
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded border px-2 py-1"
                        onClick={() =>
                          startTransition(async () => {
                            await updateIntegration(auth, String(item.id), {
                              is_enabled: !item.is_enabled,
                            });
                            refresh();
                          })
                        }
                      >
                        {item.is_enabled ? "Disable" : "Enable"}
                      </button>
                      <button
                        type="button"
                        className="rounded border px-2 py-1"
                        onClick={() =>
                          startTransition(async () => {
                            try {
                              await testIntegrationConnection(auth, String(item.id));
                              refresh();
                            } catch (e) {
                              setError(e instanceof Error ? e.message : "Connection test failed");
                              refresh();
                            }
                          })
                        }
                      >
                        Test connection
                      </button>
                      <button
                        type="button"
                        className="rounded border px-2 py-1"
                        onClick={() =>
                          startTransition(async () => {
                            try {
                              await startIntegrationSync(auth, String(item.id), "health_check");
                              refresh();
                            } catch (e) {
                              setError(e instanceof Error ? e.message : "Sync failed");
                              refresh();
                            }
                          })
                        }
                      >
                        Run sync
                      </button>
                    </div>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Sync history</h2>
        {!jobs.length ? (
          <p className="text-sm text-slate-500">No sync jobs yet.</p>
        ) : (
          <ul className="space-y-2">
            {jobs.map((job) => (
              <li key={String(job.id)} className="rounded border bg-white p-3 text-sm">
                {String(job.status)} · {String(job.direction)} · success {String(job.success_count)} / fail{" "}
                {String(job.failure_count)}
                {job.error_details ? ` · ${String(job.error_details)}` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Activity log</h2>
        {!activity.length ? (
          <p className="text-sm text-slate-500">No activity yet.</p>
        ) : (
          <ul className="space-y-2">
            {activity.map((row) => (
              <li key={String(row.id)} className="rounded border bg-white p-3 text-sm">
                <div className="font-medium">{String(row.action)}</div>
                <div className="text-slate-600">
                  {String(row.summary)} · {String(row.outcome)} · {String(row.created_at)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
