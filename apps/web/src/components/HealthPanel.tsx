"use client";

import { useEffect, useState } from "react";

interface HealthPayload {
  status: string;
  service: string;
  version: string;
}

export function HealthPanel() {
  const [data, setData] = useState<HealthPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Health check failed (${response.status})`);
        }
        return (await response.json()) as HealthPayload;
      })
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Health check failed");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <p className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800" role="alert">
        {error}
      </p>
    );
  }

  if (!data) {
    return <p className="mt-6 text-slate-600">Checking web process…</p>;
  }

  return (
    <dl className="mt-6 rounded-xl bg-white p-6 shadow-sm">
      <div className="flex justify-between py-2">
        <dt className="text-slate-500">Status</dt>
        <dd className="font-medium text-emerald-700">{data.status}</dd>
      </div>
      <div className="flex justify-between py-2">
        <dt className="text-slate-500">Service</dt>
        <dd>{data.service}</dd>
      </div>
      <div className="flex justify-between py-2">
        <dt className="text-slate-500">Version</dt>
        <dd>{data.version}</dd>
      </div>
    </dl>
  );
}
