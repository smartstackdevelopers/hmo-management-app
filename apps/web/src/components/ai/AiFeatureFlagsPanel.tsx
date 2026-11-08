"use client";

import { useCallback, useEffect, useState } from "react";
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
      <p className="text-sm text-forest-800">
        Organisation AI features are fail-closed: missing configuration means disabled. Enabling a
        feature does not bypass budgets, RBAC, or human approval. This control panel is never
        feature-flag gated.
      </p>

      {error ? <p className="text-sm text-red-800">{error}</p> : null}
      {message ? <p className="text-sm text-forest-800">{message}</p> : null}
      {state === "loading" ? <p className="text-sm text-forest-700">Loading…</p> : null}

      {state === "ready" && items.length === 0 ? (
        <p className="text-sm text-forest-700">No controllable AI features registered.</p>
      ) : null}

      <ul className="divide-y divide-forest-100 rounded-lg border border-forest-100 bg-white">
        {items.map((item) => {
          const featureId = String(item.feature_id);
          const enabled = Boolean(item.enabled);
          const pilotEligible = Boolean(item.pilot_eligible);
          const pilotEnabled = Boolean(item.pilot_enabled);
          return (
            <li key={featureId} className="space-y-2 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-forest-900">{String(item.name)}</h3>
                  <p className="text-sm text-forest-700">{String(item.description)}</p>
                  <p className="mt-1 text-xs text-forest-600">
                    {String(item.phase_feature)} · {featureId} · {statusLabel(item as never)}
                  </p>
                  <p className="text-xs text-forest-600">
                    Updated: {String(item.updated_at ?? "—")} by{" "}
                    {String(item.updated_by_user_id ?? "—")}
                  </p>
                </div>
                {canManage ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded-md bg-forest-800 px-3 py-1.5 text-sm text-white"
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
                      className="rounded-md border border-forest-200 px-3 py-1.5 text-sm"
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
            <h2 id="ff-confirm-title" className="text-lg font-semibold text-forest-900">
              Confirm configuration change
            </h2>
            <p className="text-sm text-forest-800">
              {pending.enabled ? "Enable" : "Disable"}{" "}
              <span className="font-mono text-xs">{pending.featureId}</span>?
            </p>
            <label className="block text-sm text-forest-800">
              Reason (recommended)
              <textarea
                className="mt-1 w-full rounded-md border border-forest-200 p-2 text-sm"
                rows={3}
                maxLength={2000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-forest-200 px-3 py-1.5 text-sm"
                onClick={() => setPending(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-md bg-forest-800 px-3 py-1.5 text-sm text-white"
                onClick={() => void confirmChange()}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="space-y-2">
        <h3 className="font-semibold text-forest-900">Configuration history</h3>
        {history.length === 0 ? (
          <p className="text-sm text-forest-700">No history yet.</p>
        ) : (
          <ul className="divide-y divide-forest-100 rounded-lg border border-forest-100 bg-white text-sm">
            {history.map((row) => (
              <li key={String(row.id)} className="p-3">
                <p className="font-medium text-forest-900">
                  {String(row.feature_id)} · {String(row.action)}
                </p>
                <p className="text-xs text-forest-600">
                  {String(row.event_at)} · enabled {String(row.previous_enabled)} →{" "}
                  {String(row.new_enabled)} · pilot {String(row.previous_pilot_enabled)} →{" "}
                  {String(row.new_pilot_enabled)}
                </p>
                {row.change_reason ? (
                  <p className="text-xs text-forest-700">{String(row.change_reason)}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
