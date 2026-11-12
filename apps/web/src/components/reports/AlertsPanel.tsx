"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  evaluateAlerts,
  fetchAlertThresholds,
  fetchAlerts,
  updateAlertStatus,
} from "@/lib/reportingApi";

type Props = { accessToken: string; organisationId: string; role?: string | null; canManage?: boolean };

export function AlertsPanel({ accessToken, organisationId, role, canManage }: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [thresholds, setThresholds] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState("open");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        const [a, t] = await Promise.all([
          fetchAlerts({ ...auth, status: status || undefined }),
          fetchAlertThresholds(auth),
        ]);
        setItems(a.items);
        setThresholds(t.items);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load alerts");
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Early-warning alerts</h1>
          <p className="mt-1 text-sm text-slate-600">
            Threshold-based operational warnings from live records. Does not automate housing or tenancy decisions.
          </p>
        </div>
        <div className="flex gap-2">
          <select
            className="rounded border px-2 py-1.5 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="open">open</option>
            <option value="acknowledged">acknowledged</option>
            <option value="resolved">resolved</option>
            <option value="dismissed">dismissed</option>
            <option value="">all</option>
          </select>
          {canManage ? (
            <button
              type="button"
              disabled={pending}
              className="rounded bg-teal-800 px-3 py-2 text-sm text-white disabled:opacity-60"
              onClick={() =>
                startTransition(async () => {
                  await evaluateAlerts(auth);
                  refresh();
                })
              }
            >
              Evaluate now
            </button>
          ) : null}
        </div>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-2 text-sm font-medium text-slate-800">Configured thresholds</h2>
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {thresholds.map((t) => (
            <li key={String(t.alert_type)} className="rounded border border-slate-100 p-2 text-sm">
              <div className="font-medium">{String(t.alert_type).replaceAll("_", " ")}</div>
              <div className="text-slate-600">
                threshold {String(t.threshold_value)} · {t.is_enabled ? "enabled" : "disabled"}
              </div>
            </li>
          ))}
        </ul>
      </div>

      {!items.length ? (
        <p className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
          No alerts in this status.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((alert) => (
            <li key={String(alert.id)} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="font-medium text-slate-900">{String(alert.title)}</div>
                  <div className="mt-1 text-sm text-slate-600">{String(alert.reason)}</div>
                  <div className="mt-2 text-xs text-slate-500">
                    {String(alert.alert_type)} · {String(alert.severity)} · metric {String(alert.metric_value)} /
                    threshold {String(alert.threshold_value)} · created {String(alert.created_at ?? "")}
                  </div>
                </div>
                <div className="flex gap-2">
                  {["acknowledged", "resolved", "dismissed"].map((s) => (
                    <button
                      key={s}
                      type="button"
                      className="rounded border px-2 py-1 text-xs capitalize"
                      onClick={() =>
                        startTransition(async () => {
                          await updateAlertStatus(auth, String(alert.id), s);
                          refresh();
                        })
                      }
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
