import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type BackupAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function bFetch<T>(path: string, options: BackupAuth, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export function fetchBackupDashboard(options: BackupAuth) {
  return bFetch<Record<string, unknown>>("/api/v1/backups/dashboard", options);
}

export function fetchBackupHistory(options: BackupAuth) {
  return bFetch<Record<string, unknown>[]>("/api/v1/backups/history", options);
}

export function runConfigBackup(options: BackupAuth) {
  return bFetch<Record<string, unknown>>("/api/v1/backups/run", options, {
    method: "POST",
    body: JSON.stringify({ backup_type: "config_manifest", force: true }),
  });
}
