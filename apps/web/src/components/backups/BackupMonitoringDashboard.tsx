"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { fetchBackupDashboard, fetchBackupHistory, runConfigBackup, type BackupAuth } from "@/lib/backupsApi";

type Props = BackupAuth & { canManage: boolean };

export function BackupMonitoringDashboard({ accessToken, organisationId, role, canManage }: Props) {
  const auth = { accessToken, organisationId, role };
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [history, setHistory] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [d, h] = await Promise.all([fetchBackupDashboard(auth), fetchBackupHistory(auth)]);
      setDash(d);
      setHistory(h);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load backups");
    }
  }, [accessToken, organisationId, role]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <ErrorState description={error} />;
  if (!dash) return <p className="text-sm text-slate-600">Loading backup monitoring…</p>;

  const issues = (dash.outstanding_issues ?? []) as string[];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-900">Backup monitoring</h1>
      <p className="text-sm text-amber-900 rounded border border-amber-200 bg-amber-50 p-3">
        Platform backups only. RPO/RTO targets remain pending organisational approval. Never download database dumps
        without authorisation.
      </p>
      <BackupMetrics dash={dash} />
      {canManage ? (
        <button
          type="button"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white"
          onClick={async () => {
            await runConfigBackup(auth);
            await load();
          }}
        >
          Run config manifest backup (test-safe)
        </button>
      ) : null}
      <section>
        <h2 className="text-sm font-medium">Outstanding issues</h2>
        <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
          {issues.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="text-sm font-medium">History ({history.length})</h2>
        <ul className="mt-2 text-sm text-slate-700">
          {history.slice(0, 10).map((row) => (
            <li key={String(row.id)}>
              {String(row.backup_type)} — {String(row.status)} — {String(row.verification_status)}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function BackupMetrics({ dash }: { dash: Record<string, unknown> }) {
  const items: [string, unknown][] = [
    ["Enabled", dash.backup_enabled],
    ["pg_dump", dash.pg_dump_available],
    ["Pending jobs", dash.pending_jobs],
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">{label}</p>
          <p className="text-lg font-semibold">{String(value ?? "—")}</p>
        </div>
      ))}
    </div>
  );
}
