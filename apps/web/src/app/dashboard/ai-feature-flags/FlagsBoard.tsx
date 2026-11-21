"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { Card, CardHeader, DataTable, StatusChip, Td, Th, btnPrimary, btnSecondary, humanize, inputClass, labelClass } from "@/components/ui/primitives";
import { canManageAiFeatureFlags } from "@/lib/aiFeatureFlagsView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

type FlagItem = Record<string, unknown>;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function groupOf(name: string): "Case & notes" | "Tenant facing" | "Operations" {
  const text = name.toLowerCase();
  if (/tenant|voice|cv /.test(text)) return "Tenant facing";
  if (/note|case summar|duplicate/.test(text)) return "Case & notes";
  return "Operations";
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

export function FlagsBoard(props: Props) {
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [items, setItems] = useState<FlagItem[]>([]);
  const [history, setHistory] = useState<FlagItem[]>([]);
  const [group, setGroup] = useState("All features");
  const [pending, setPending] = useState<{ featureId: string; name: string; enabled: boolean; pilot: boolean } | null>(null);
  const [reason, setReason] = useState("");
  const canManage = canManageAiFeatureFlags(props.permissions);

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  const load = useCallback(async () => {
    setError(null);
    setState("loading");
    try {
      const [cfg, hist] = await Promise.all([
        fetch(`${API_BASE}/api/v1/ai-feature-flags`, { headers: headers() }),
        fetch(`${API_BASE}/api/v1/ai-feature-flags/history?limit=30`, { headers: headers() }),
      ]);
      if (!cfg.ok) {
        setError("AI feature flags could not be loaded.");
        setState("error");
        return;
      }
      const payload = (await cfg.json()) as { items: FlagItem[] };
      setItems(payload.items ?? []);
      if (hist.ok) {
        const historyPayload = (await hist.json()) as { items: FlagItem[] };
        setHistory(historyPayload.items ?? []);
      }
      setState("ready");
    } catch {
      setError("AI feature flags could not be loaded.");
      setState("error");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.accessToken, props.organisationId, props.role]);

  useEffect(() => {
    void load();
  }, [load]);

  const names = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of items) map.set(String(item.feature_id), String(item.name || "Feature"));
    return map;
  }, [items]);

  const groups = ["All features", "Case & notes", "Tenant facing", "Operations"].filter(
    (label) => label === "All features" || items.some((item) => groupOf(String(item.name || "")) === label),
  );
  const visible = items.filter((item) => group === "All features" || groupOf(String(item.name || "")) === group);
  const sections = Array.from(new Set(visible.map((item) => groupOf(String(item.name || "")))));

  async function confirmChange() {
    if (!pending || !canManage) return;
    setMessage(null);
    const response = await fetch(`${API_BASE}/api/v1/ai-feature-flags/${pending.featureId}`, {
      method: "PUT",
      headers: headers(),
      body: JSON.stringify({
        enabled: pending.enabled,
        pilot_enabled: pending.pilot,
        change_reason: reason.trim() || null,
      }),
    });
    if (!response.ok) {
      setError("The feature setting could not be saved.");
      setPending(null);
      return;
    }
    setMessage(pending.enabled ? `${pending.name} is on. Usage limits and human approval still apply.` : `${pending.name} is off.`);
    setPending(null);
    setReason("");
    await load();
  }

  if (state === "error" && items.length === 0) {
    return <ErrorState description={error || "AI feature flags could not be loaded."} retryHref="/dashboard/ai-feature-flags" />;
  }

  return (
    <div className="space-y-6">
      {error ? <ErrorState description={error} /> : null}
      {message ? <p className="text-sm text-slate-700">{message}</p> : null}
      {state === "loading" && items.length === 0 ? <p className="text-sm text-slate-500">Loading feature settings…</p> : null}
      {state === "ready" && items.length === 0 ? (
        <EmptyState title="No AI features" description="Controllable AI features will appear here when they are registered for this organisation." />
      ) : null}

      {items.length > 0 ? (
        <div className="grid items-start gap-4 lg:grid-cols-[14rem_minmax(0,1fr)]">
          <Card>
            <nav aria-label="Feature groups" className="space-y-1">
              {groups.map((label) => (
                <button
                  key={label}
                  type="button"
                  aria-current={group === label ? "true" : undefined}
                  onClick={() => setGroup(label)}
                  className={`block w-full rounded-lg px-3 py-2 text-left text-sm font-medium ${
                    group === label ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {label}
                </button>
              ))}
            </nav>
          </Card>
          <div className="space-y-4">
            {sections.map((section) => (
              <Card key={section}>
                <CardHeader title={section} />
                <ul className="divide-y divide-slate-100">
                  {visible
                    .filter((item) => groupOf(String(item.name || "")) === section)
                    .map((item) => {
                      const enabled = Boolean(item.enabled);
                      const name = String(item.name || "Feature");
                      return (
                        <li key={String(item.feature_id)} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                          <div className="min-w-0">
                            <p className="font-semibold text-slate-900">{name}</p>
                            <p className="mt-0.5 text-sm text-slate-500">{String(item.description || "")}</p>
                          </div>
                          {canManage ? (
                            <button
                              type="button"
                              role="switch"
                              aria-checked={enabled}
                              aria-label={`${enabled ? "Turn off" : "Turn on"} ${name}`}
                              onClick={() =>
                                setPending({
                                  featureId: String(item.feature_id),
                                  name,
                                  enabled: !enabled,
                                  pilot: !enabled && Boolean(item.pilot_eligible),
                                })
                              }
                              className={`relative h-6 w-11 shrink-0 rounded-full transition ${enabled ? "bg-brand-700" : "bg-slate-200"}`}
                            >
                              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow ${enabled ? "left-5" : "left-0.5"}`} />
                            </button>
                          ) : (
                            <StatusChip status={enabled ? "active" : "disabled"}>{enabled ? "On" : "Off"}</StatusChip>
                          )}
                        </li>
                      );
                    })}
                </ul>
              </Card>
            ))}
          </div>
        </div>
      ) : null}

      <section id="flag-history" className="space-y-3">
        <h2 className="text-base font-semibold text-slate-900">History</h2>
        {history.length === 0 ? (
          <EmptyState title="No changes yet" description="Each change to a feature setting is recorded here." />
        ) : (
          <DataTable caption="AI feature flag history">
            <thead>
              <tr>
                <Th>Feature</Th>
                <Th>Change</Th>
                <Th>When</Th>
                <Th>Result</Th>
              </tr>
            </thead>
            <tbody>
              {history.map((row) => {
                const name = names.get(String(row.feature_id)) || "Feature";
                const on = row.new_enabled === true || row.new_enabled === "true";
                return (
                  <tr key={String(row.id)}>
                    <Td className="font-semibold text-slate-900">{name}</Td>
                    <Td>{humanize(String(row.action ?? "updated"))}</Td>
                    <Td className="whitespace-nowrap text-slate-500">{whenLabel(row.event_at ?? row.created_at)}</Td>
                    <Td>
                      <StatusChip status={on ? "active" : "disabled"}>{on ? "On" : "Off"}</StatusChip>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
        )}
        <p className="text-xs text-slate-500">
          Showing {history.length === 0 ? "0" : `1–${history.length}`} of {history.length}
        </p>
      </section>

      {pending ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" role="dialog" aria-modal="true" aria-labelledby="flag-confirm-title">
          <form
            className="w-full max-w-md space-y-4 rounded-2xl bg-white p-5 shadow-card"
            onSubmit={(event) => {
              event.preventDefault();
              void confirmChange();
            }}
          >
            <h2 id="flag-confirm-title" className="text-lg font-semibold text-slate-900">
              {pending.enabled ? "Turn on" : "Turn off"} {pending.name}
            </h2>
            <p className="text-sm text-slate-600">Usage limits and human approval still apply. This change is audited.</p>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="flag-reason">
                Reason
              </label>
              <textarea id="flag-reason" className={`${inputClass} h-auto py-2`} rows={3} maxLength={2000} value={reason} onChange={(event) => setReason(event.target.value)} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className={btnSecondary} onClick={() => setPending(null)}>
                Cancel
              </button>
              <button type="submit" className={btnPrimary}>
                Confirm
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
