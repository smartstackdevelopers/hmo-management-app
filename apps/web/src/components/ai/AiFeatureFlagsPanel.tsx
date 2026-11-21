"use client";

import { useCallback, useEffect, useState } from "react";
import { StatusChip } from "@/components/ui/primitives";
import { canManageAiFeatureFlags, statusLabel } from "@/lib/aiFeatureFlagsView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type FlagItem = Record<string, unknown>;

export function AiFeatureFlagsPanel(props: Props) {
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [items, setItems] = useState<FlagItem[]>([]);
  const [history, setHistory] = useState<FlagItem[]>([]);
  const [pending, setPending] = useState<{
    featureId: string;
    enabled: boolean;
    pilot: boolean;
  } | null>(null);
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
        setError(await cfg.text());
        setState("error");
        return;
      }
      const payload = (await cfg.json()) as { items: FlagItem[] };
      setItems(payload.items ?? []);
      if (hist.ok) {
        const h = (await hist.json()) as { items: FlagItem[] };
        setHistory(h.items ?? []);
      }
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load AI feature flags");
      setState("error");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.accessToken, props.organisationId, props.role]);

  useEffect(() => {
    void load();
  }, [load]);

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
      setError(await response.text());
      setPending(null);
      return;
    }
    setMessage(
      pending.enabled
        ? `Enabled ${pending.featureId}. Usage caps and human approval still apply.`
        : `Disabled ${pending.featureId}. New executions are blocked.`,
    );
    setPending(null);
    setReason("");
    await load();
  }

  return (
    <section className="space-y-6">
      <p className="text-sm text-slate-700">
        Organisation AI features are fail-closed: missing configuration means disabled. Enabling a
        feature does not bypass budgets, RBAC, or human approval. This control panel is never
        feature-flag gated.
      </p>

      {error ? <p className="text-sm text-red-800">{error}</p> : null}
      {message ? <p className="text-sm text-slate-700">{message}</p> : null}
      {state === "loading" ? <p className="text-sm text-slate-600">Loading…</p> : null}

      {state === "ready" && items.length === 0 ? (
        <p className="text-sm text-slate-600">No controllable AI features registered.</p>
      ) : null}

      <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
        {items.map((item) => {
          const featureId = String(item.feature_id);
          const enabled = Boolean(item.enabled);
          const pilotEligible = Boolean(item.pilot_eligible);
          const pilotEnabled = Boolean(item.pilot_enabled);
          return (
            <li key={featureId} className="space-y-2 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-slate-900">{String(item.name)}</h3>
                    <StatusChip status={enabled ? "active" : "disabled"}>{enabled ? "On" : "Off"}</StatusChip>
                  </div>
                  <p className="text-sm text-slate-600">{String(item.description)}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {String(item.phase_feature)} · {featureId} · {statusLabel(item as never)}
                  </p>
                  <p className="text-xs text-slate-500">
                    Updated: {String(item.updated_at ?? "—")} by{" "}
                    {String(item.updated_by_user_id ?? "—")}
                  </p>
                </div>
                {canManage ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
                      onClick={() =>
                        setPending({
                          featureId,
                          enabled: true,
                          pilot: pilotEligible ? true : false,
                        })
                      }
                    >
                      Enable{pilotEligible ? " pilot" : ""}
                    </button>
                    <button
                      type="button"
                      className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                      onClick={() =>
                        setPending({
                          featureId,
                          enabled: false,
                          pilot: false,
                        })
                      }
                      disabled={!enabled && !pilotEnabled}
                    >
                      Disable
                    </button>
                  </div>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>

      {pending ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ff-confirm-title"
        >
          <div className="w-full max-w-md space-y-3 rounded-lg bg-white p-4 shadow-lg">
            <h2 id="ff-confirm-title" className="text-lg font-semibold text-slate-900">
              Confirm configuration change
            </h2>
            <p className="text-sm text-slate-700">
              {pending.enabled ? "Enable" : "Disable"}{" "}
              <span className="font-mono text-xs">{pending.featureId}</span>?
            </p>
            <label className="block text-sm text-slate-700">
              Reason (recommended)
              <textarea
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
                rows={3}
                maxLength={2000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                onClick={() => setPending(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
                onClick={() => void confirmChange()}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="space-y-2">
        <h3 className="font-semibold text-slate-900">Configuration history</h3>
        {history.length === 0 ? (
          <p className="text-sm text-slate-600">No history yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100 bg-white text-sm">
            {history.map((row) => (
              <li key={String(row.id)} className="p-3">
                <p className="font-medium text-slate-900">
                  {String(row.feature_id)} · {String(row.action)}
                </p>
                <p className="text-xs text-slate-500">
                  {String(row.event_at)} · enabled {String(row.previous_enabled)} →{" "}
                  {String(row.new_enabled)} · pilot {String(row.previous_pilot_enabled)} →{" "}
                  {String(row.new_pilot_enabled)}
                </p>
                {row.change_reason ? (
                  <p className="text-xs text-slate-600">{String(row.change_reason)}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
