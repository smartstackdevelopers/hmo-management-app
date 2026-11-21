"use client";

import { useEffect, useState } from "react";
import { StatusChip } from "@/components/ui/primitives";

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
      <p className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
        {error}
      </p>
    );
  }

  if (!data) {
    return (
      <p className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-card" role="status">
        Checking service status…
      </p>
    );
  }

  return (
    <dl className="mt-6 divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white px-5 shadow-card">
      <div className="flex items-center justify-between py-3.5">
        <dt className="text-sm text-slate-500">Status</dt>
        <dd>
          <StatusChip status={data.status}>{data.status}</StatusChip>
        </dd>
      </div>
      <div className="flex items-center justify-between py-3.5">
        <dt className="text-sm text-slate-500">Service</dt>
        <dd className="text-sm font-medium text-slate-900">{data.service}</dd>
      </div>
      <div className="flex items-center justify-between py-3.5">
        <dt className="text-sm text-slate-500">Version</dt>
        <dd className="text-sm font-medium text-slate-900">{data.version}</dd>
      </div>
    </dl>
  );
}
