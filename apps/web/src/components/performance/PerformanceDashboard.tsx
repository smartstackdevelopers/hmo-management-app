"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { fetchPerformanceDashboard, runPerformanceBenchmark, type PerfAuth } from "@/lib/performanceApi";

export function PerformanceDashboard({ accessToken, organisationId, role, canRun }: PerfAuth & { canRun: boolean }) {
  const auth = { accessToken, organisationId, role };
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDash(await fetchPerformanceDashboard(auth));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load performance data");
    }
  }, [accessToken, organisationId, role]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <ErrorState description={error} />;
  if (!dash) {
    return (
      <p className="text-sm text-slate-700" role="status" aria-live="polite">
        Loading performance metrics…
      </p>
    );
  }

  const slow = (dash.slowest_journeys_p95 ?? []) as Record<string, unknown>[];
  const latest = (dash.latest_run ?? {}) as Record<string, unknown>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Performance monitoring</h1>
      <p className="text-sm text-slate-600">
        Measured synthetic journey probes (auth gates + health). Capacity targets:{" "}
        {String(dash.capacity_targets)}. Sentry: {String(dash.sentry_configured)}.
      </p>
      {canRun ? (
        <button
          type="button"
          className="min-h-11 rounded-md bg-slate-900 px-4 py-2 text-sm text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
          onClick={async () => {
            await runPerformanceBenchmark(auth, 5);
            await load();
          }}
        >
          Run benchmark (5 samples)
        </button>
      ) : null}
      <pre className="max-h-48 overflow-auto rounded border bg-slate-50 p-3 text-xs">
        {JSON.stringify(latest.summary ?? {}, null, 2)}
      </pre>
      <section>
        <h2 className="text-sm font-medium">Slowest journeys (p95)</h2>
        <ul className="mt-2 text-sm">
          {slow.map((j) => (
            <li key={String(j.journey_key)}>
              {String(j.journey_key)} — p95 {String(j.p95_ms)} ms
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
