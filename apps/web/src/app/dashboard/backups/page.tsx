import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, DataTable, StatCard, StatGrid, StatusChip, Td, Th, humanize } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchBackupDashboard, fetchBackupHistory } from "@/lib/backupsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { RunBackupButton } from "./RunBackupButton";

const READ = ["backup.read", "backup.manage"];

function whenLabel(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/London",
  }).format(date);
}

function plainIssue(issue: string): string {
  if (issue.startsWith("BACKUP_ENABLED")) return "Scheduled backups are switched off.";
  if (issue.includes("BACKUP_S3_BUCKET")) return "Off-host backup storage is not configured for production.";
  if (issue.startsWith("pg_dump")) return "Database backup tools are not available on the server.";
  if (issue.startsWith("No verified backup")) return "No verified backup is on record yet.";
  return issue;
}

export default async function BackupsPage() {
  const session = await requireAuthenticatedSession("/dashboard/backups");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see backups." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so backups can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/backups" />;
  const canManage = canAny(session.authorization?.permissions ?? [], ["backup.manage"]);
  const auth = { accessToken: token, organisationId: orgId, role: session.authorization?.active_role };

  let dash: Record<string, unknown>;
  let history: Record<string, unknown>[] = [];
  try {
    [dash, history] = await Promise.all([fetchBackupDashboard(auth), fetchBackupHistory(auth)]);
  } catch {
    return (
      <ErrorState
        title="Couldn't load backups"
        description="Something went wrong on our side. Please try again."
        retryHref="/dashboard/backups"
      />
    );
  }

  const issues = Array.isArray(dash.outstanding_issues) ? (dash.outstanding_issues as string[]) : [];
  const latest = (dash.latest_backup ?? null) as Record<string, unknown> | null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Platform"
        title="Backups"
        description="Platform backups only. Recovery targets stay pending until the organisation approves them."
        actions={canManage ? <RunBackupButton {...auth} /> : null}
      />
      <StatGrid>
        <StatCard label="Backups" value={dash.backup_enabled ? "On" : "Off"} tone={dash.backup_enabled ? "green" : "amber"} />
        <StatCard label="Database tools" value={dash.pg_dump_available ? "Available" : "Missing"} tone={dash.pg_dump_available ? "green" : "red"} />
        <StatCard label="Pending jobs" value={String(dash.pending_jobs ?? 0)} />
        <StatCard label="Latest" value={latest?.status ? humanize(String(latest.status)) : "None"} />
      </StatGrid>
      {issues.length > 0 ? (
        <Card>
          <h2 className="text-base font-semibold text-slate-900">Outstanding issues</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {issues.map((issue) => (
              <li key={issue}>{plainIssue(issue)}</li>
            ))}
          </ul>
        </Card>
      ) : null}
      {history.length === 0 ? (
        <EmptyState title="No backup history" description="Completed backup runs will be listed here." />
      ) : (
        <DataTable caption="Backup history">
          <thead>
            <tr>
              <Th>Type</Th>
              <Th>Started</Th>
              <Th>Status</Th>
              <Th>Verification</Th>
            </tr>
          </thead>
          <tbody>
            {history.map((row) => (
              <tr key={String(row.id)}>
                <Td className="font-semibold text-slate-900">{humanize(String(row.backup_type ?? ""))}</Td>
                <Td className="whitespace-nowrap text-slate-500">{whenLabel(row.started_at)}</Td>
                <Td>
                  <StatusChip status={String(row.status ?? "")} />
                </Td>
                <Td>
                  <StatusChip status={String(row.verification_status ?? "")} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {history.length === 0 ? "0" : `1–${history.length}`} of {history.length}
      </p>
    </div>
  );
}
