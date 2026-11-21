import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatCard, StatGrid, StatusChip, Td, Th, humanize } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchPerformanceDashboard } from "@/lib/performanceApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { RunBenchmarkButton } from "./RunBenchmarkButton";

const READ = ["performance.read", "performance.benchmark.run", "platform.monitoring.read"];

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

export default async function PerformancePage() {
  const session = await requireAuthenticatedSession("/dashboard/performance");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see performance." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so performance can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/performance" />;
  const canRun = canAny(session.authorization?.permissions ?? [], ["performance.benchmark.run"]);

  let dash: Record<string, unknown>;
  try {
    dash = await fetchPerformanceDashboard({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
  } catch {
    return (
      <ErrorState
        title="Couldn't load performance"
        description="Something went wrong on our side. Please try again."
        retryHref="/dashboard/performance"
      />
    );
  }

  const latest = (dash.latest_run ?? {}) as Record<string, unknown>;
  const slow = Array.isArray(dash.slowest_journeys_p95) ? (dash.slowest_journeys_p95 as Record<string, unknown>[]) : [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Platform"
        title="Performance"
        description="Measured journey probes from the latest benchmark run."
        actions={
          canRun ? (
            <RunBenchmarkButton
              accessToken={token}
              organisationId={orgId}
              role={session.authorization?.active_role}
            />
          ) : null
        }
      />
      <StatGrid>
        <StatCard label="Latest run" value={latest.status ? humanize(String(latest.status)) : "None"} />
        <StatCard label="Started" value={whenLabel(latest.started_at)} />
        <StatCard label="Journeys measured" value={slow.length} />
        <StatCard
          label="Error reporting"
          value={dash.sentry_configured ? "Configured" : "Not configured"}
          tone={dash.sentry_configured ? "green" : "gray"}
        />
      </StatGrid>
      {slow.length === 0 ? (
        <EmptyState
          title="No benchmark results"
          description="Run a benchmark to record journey times. Capacity targets stay pending until they are approved."
        />
      ) : (
        <DataTable caption="Slowest journeys">
          <thead>
            <tr>
              <Th>Journey</Th>
              <Th>Category</Th>
              <Th>Average</Th>
              <Th>95th percentile</Th>
            </tr>
          </thead>
          <tbody>
            {slow.map((row) => (
              <tr key={String(row.journey_key)}>
                <Td className="font-semibold text-slate-900">{humanize(String(row.journey_key ?? ""))}</Td>
                <Td>{row.category ? humanize(String(row.category)) : "—"}</Td>
                <Td>{row.avg_ms == null ? "—" : `${String(row.avg_ms)} ms`}</Td>
                <Td>{row.p95_ms == null ? "—" : `${String(row.p95_ms)} ms`}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {slow.length === 0 ? "0" : `1–${slow.length}`} of {slow.length}
        {dash.capacity_targets ? ` · Capacity ${humanize(String(dash.capacity_targets)).toLowerCase()}` : ""}
      </p>
    </div>
  );
}
