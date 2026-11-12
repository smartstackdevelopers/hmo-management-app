"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  createSchedule,
  fetchScheduleRuns,
  fetchSchedules,
  retryScheduleRun,
  updateSchedule,
} from "@/lib/reportingApi";

type Props = { accessToken: string; organisationId: string; role?: string | null };

export function SchedulesPanel({ accessToken, organisationId, role }: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [runs, setRuns] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [name, setName] = useState("Weekly housing summary");
  const [category, setCategory] = useState("housing");
  const [frequency, setFrequency] = useState("weekly");
  const [format, setFormat] = useState("csv");
  const [periodDays, setPeriodDays] = useState(7);
  const [recipients, setRecipients] = useState("");

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        const [s, r] = await Promise.all([fetchSchedules(auth), fetchScheduleRuns(auth)]);
        setItems(s.items);
        setRuns(r.items);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load schedules");
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onCreate = () => {
    startTransition(async () => {
      try {
        await createSchedule(auth, {
          name,
          report_category: category,
          frequency,
          export_format: format,
          period_days: periodDays,
          recipient_user_ids: recipients
            .split(",")
            .map((x) => x.trim())
            .filter(Boolean),
          is_enabled: true,
        });
        refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Create failed");
      }
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Scheduled reports</h1>
        <p className="mt-1 text-sm text-slate-600">
          Daily, weekly or monthly delivery to authorised organisation members only.
        </p>
      </div>
      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}

      <div className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-2">
        <label className="text-sm">
          Name
          <input className="mt-1 w-full rounded border px-2 py-1.5" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="text-sm">
          Category
          <select className="mt-1 w-full rounded border px-2 py-1.5" value={category} onChange={(e) => setCategory(e.target.value)}>
            {["housing", "complaints", "caseload", "occupancy", "plans", "dashboard"].map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Frequency
          <select className="mt-1 w-full rounded border px-2 py-1.5" value={frequency} onChange={(e) => setFrequency(e.target.value)}>
            <option value="daily">daily</option>
            <option value="weekly">weekly</option>
            <option value="monthly">monthly</option>
          </select>
        </label>
        <label className="text-sm">
          Format
          <select className="mt-1 w-full rounded border px-2 py-1.5" value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="csv">csv</option>
            <option value="pdf">pdf</option>
            <option value="xlsx">xlsx</option>
          </select>
        </label>
        <label className="text-sm">
          Period days
          <input
            type="number"
            min={1}
            max={366}
            className="mt-1 w-full rounded border px-2 py-1.5"
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
          />
        </label>
        <label className="text-sm md:col-span-2">
          Recipient user IDs (comma-separated, same organisation)
          <input
            className="mt-1 w-full rounded border px-2 py-1.5"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            placeholder="uuid, uuid"
          />
        </label>
        <button
          type="button"
          disabled={pending}
          onClick={onCreate}
          className="rounded bg-teal-800 px-3 py-2 text-sm font-medium text-white disabled:opacity-60 md:col-span-2"
        >
          Create schedule
        </button>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Schedules</h2>
        {!items.length ? (
          <p className="text-sm text-slate-500">No scheduled reports yet.</p>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={String(item.id)} className="flex flex-wrap items-center justify-between gap-2 rounded border bg-white p-3 text-sm">
                <div>
                  <div className="font-medium">{String(item.name)}</div>
                  <div className="text-slate-600">
                    {String(item.report_category)} · {String(item.frequency)} · {String(item.export_format)} ·{" "}
                    {item.is_enabled ? "enabled" : "disabled"}
                  </div>
                </div>
                <button
                  type="button"
                  className="rounded border px-2 py-1"
                  onClick={() =>
                    startTransition(async () => {
                      await updateSchedule(auth, String(item.id), { is_enabled: !item.is_enabled });
                      refresh();
                    })
                  }
                >
                  {item.is_enabled ? "Disable" : "Enable"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Run history</h2>
        {!runs.length ? (
          <p className="text-sm text-slate-500">No runs yet.</p>
        ) : (
          <ul className="space-y-2">
            {runs.map((run) => (
              <li key={String(run.id)} className="flex flex-wrap items-center justify-between gap-2 rounded border bg-white p-3 text-sm">
                <div>
                  <div>
                    {String(run.status)} · attempts {String(run.attempt_count)}
                  </div>
                  <div className="text-slate-600">{String(run.error_message ?? run.created_at ?? "")}</div>
                </div>
                {run.status === "failed" ? (
                  <button
                    type="button"
                    className="rounded border px-2 py-1"
                    onClick={() =>
                      startTransition(async () => {
                        await retryScheduleRun(auth, String(run.id));
                        refresh();
                      })
                    }
                  >
                    Retry
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
