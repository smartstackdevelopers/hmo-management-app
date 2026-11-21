"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  evaluateAlerts,
  fetchAlertThresholds,
  fetchAlerts,
  updateAlertStatus,
  upsertAlertThreshold,
} from "@/lib/reportingApi";

type Props = { accessToken: string; organisationId: string; role?: string | null; canManage?: boolean };

export function AlertsPanel({ accessToken, organisationId, role, canManage }: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [thresholds, setThresholds] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState("open");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [editType, setEditType] = useState("");
  const [editValue, setEditValue] = useState("5");
  const [editEnabled, setEditEnabled] = useState(true);

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
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">Insights</p>
          <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900">Early-warning alerts</h1>
          <p className="mt-1 text-sm text-slate-600">
            Threshold-based operational warnings from live records. Does not automate housing or tenancy decisions.
          </p>
        </div>
        <div className="flex gap-2">
          <select
            className="block h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
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
              className="inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
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

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card space-y-3">
        <h2 className="text-sm font-medium text-slate-800">Configured thresholds</h2>
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {thresholds.map((t) => (
            <li key={String(t.alert_type)} className="rounded border border-slate-100 p-2 text-sm">
              <div className="font-medium">{String(t.alert_type).replaceAll("_", " ")}</div>
              <div className="text-slate-600">
                threshold {String(t.threshold_value)} · {t.is_enabled ? "enabled" : "disabled"}
              </div>
              {canManage ? (
                <button
                  type="button"
                  className="mt-2 text-xs text-brand-700 underline"
                  onClick={() => {
                    setEditType(String(t.alert_type));
                    setEditValue(String(t.threshold_value ?? "5"));
                    setEditEnabled(Boolean(t.is_enabled));
                  }}
                >
                  Edit
                </button>
              ) : null}
            </li>
          ))}
        </ul>
        {canManage ? (
          <div className="flex flex-wrap items-end gap-2 border-t border-slate-100 pt-3">
            <label className="text-xs">
              Alert type
              <input
                className="mt-1 block block h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
                value={editType}
                onChange={(e) => setEditType(e.target.value)}
                placeholder="e.g. high_vacancy"
              />
            </label>
            <label className="text-xs">
              Threshold
              <input
                type="number"
                min={0}
                className="mt-1 block w-24 block h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
              />
            </label>
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={editEnabled} onChange={(e) => setEditEnabled(e.target.checked)} />
              Enabled
            </label>
            <button
              type="button"
              disabled={pending || !editType.trim()}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
              onClick={() =>
                startTransition(async () => {
                  try {
                    await upsertAlertThreshold(auth, {
                      alert_type: editType.trim(),
                      threshold_value: Number(editValue) || 0,
                      is_enabled: editEnabled,
                    });
                    refresh();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Threshold save failed");
                  }
                })
              }
            >
              Save threshold
            </button>
          </div>
        ) : null}
      </div>

      {!items.length ? (
        <p className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
          No alerts in this status.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((alert) => (
            <li key={String(alert.id)} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
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
                      className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 text-xs capitalize"
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
