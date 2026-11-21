import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, btnSecondary, DataTable, FilterTabs, humanize, inputClass, StatCard, StatGrid, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { getSafeguardingDashboard, listSafeguardingAlerts } from "@/lib/safeguardingAlertsApi";

const READ = ["safeguarding_alerts.read", "safeguarding_alerts.manage"];

function text(value: unknown): string {
  return value == null || value === "" ? "—" : String(value);
}

function shortId(value: string): string {
  return value.length > 10 ? `…${value.slice(-6)}` : value;
}

function formatRaised(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const minutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const startToday = new Date();
  startToday.setHours(0, 0, 0, 0);
  const startThat = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDiff = Math.round((startToday.getTime() - startThat.getTime()) / 86400000);
  if (dayDiff === 1) return "Yesterday";
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function alertsHref(next: { q?: string; status?: string }) {
  const search = new URLSearchParams();
  if (next.q) search.set("q", next.q);
  if (next.status) search.set("status", next.status);
  const query = search.toString();
  return query ? `/dashboard/safeguarding-alerts?${query}` : "/dashboard/safeguarding-alerts";
}

export default async function SafeguardingAlertsPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string; status?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
  const session = await requireAuthenticatedSession("/dashboard/safeguarding-alerts");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see safeguarding alerts." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/safeguarding-alerts" />;
  let stats: Record<string, unknown> = {};
  let alerts: Record<string, unknown>[] = [];
  try {
    stats = await getSafeguardingDashboard(token, orgId);
    alerts = await listSafeguardingAlerts(token, orgId);
  } catch {
    return (
      <ErrorState description="Safeguarding alerts stay off until the organisation turns the add-on on." retryHref="/dashboard/safeguarding-alerts" />
    );
  }
  const byStatus = (stats.by_status ?? {}) as Record<string, number>;
  const canReport = canAny(session.authorization?.permissions, ["safeguarding.reminders.manage", "safeguarding.reminders.manage.assigned", "safeguarding_alerts.manage"]);
  const q = (params.q ?? "").trim().toLowerCase();
  const knownStatuses = [
    ...new Set([
      ...Object.entries(byStatus)
        .filter(([, count]) => Number(count) > 0)
        .map(([key]) => key),
      ...alerts.map((alert) => text(alert.status)).filter((status) => status !== "—"),
    ]),
  ].sort();
  const status = knownStatuses.includes(params.status ?? "") ? params.status ?? "" : "";
  const visible = alerts.filter((alert) => {
    if (status && text(alert.status) !== status) return false;
    if (!q) return true;
    return [alert.reference_number, alert.description, alert.tenant_id, alert.source, alert.category_slug]
      .some((value) => text(value).toLowerCase().includes(q));
  });
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Safety"
        title="Safeguarding alerts"
        description="Acknowledge within 1 hour. Escalate when in doubt. Alerts do not decide an outcome."
        actions={
          canReport ? (
            <Link href="/dashboard/safeguarding/new" className={btnPrimary}>
              Report concern
            </Link>
          ) : null
        }
      />
      <StatGrid>
        <StatCard label="New" value={text(byStatus.new ?? 0)} tone="blue" />
        <StatCard label="Under review" value={text(byStatus.under_review ?? 0)} tone="amber" />
        <StatCard label="Closed" value={text(byStatus.closed ?? 0)} />
        <StatCard label="Overdue follow-ups" value={text(stats.overdue_follow_ups ?? 0)} tone="red" hint={Number(stats.critical_open ?? 0) > 0 ? `${text(stats.critical_open)} critical` : undefined} />
      </StatGrid>
      <div className="flex flex-wrap items-center gap-3">
        <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
          {status ? <input type="hidden" name="status" value={status} /> : null}
          <label className="sr-only" htmlFor="alert-search">
            Search alerts
          </label>
          <input id="alert-search" name="q" defaultValue={params.q ?? ""} placeholder="Search reference, tenant or description" className={inputClass} />
          <button type="submit" className={btnSecondary}>
            Search
          </button>
        </form>
        <FilterTabs
          tabs={[
            { label: "All", href: alertsHref({ q: params.q }), active: !status },
            ...knownStatuses.map((item) => ({
              label: humanize(item),
              href: alertsHref({ q: params.q, status: item }),
              active: status === item,
              count: typeof byStatus[item] === "number" ? byStatus[item] : undefined,
            })),
          ]}
        />
      </div>
      {visible.length === 0 ? (
        <EmptyState
          title="No alerts recorded"
          description={q || status ? "No alerts match this search or status." : "Alerts raised for this organisation will appear here."}
          action={q || status ? { label: "Clear filters", href: "/dashboard/safeguarding-alerts" } : undefined}
        />
      ) : (
        <DataTable caption="Safeguarding alerts">
          <thead>
            <tr>
              <Th>Tenant</Th>
              <Th>Alert</Th>
              <Th>Source</Th>
              <Th>Raised</Th>
              <Th>Severity</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((alert) => {
              const tenantId = text(alert.tenant_id);
              return (
                <tr key={text(alert.id)} className="hover:bg-slate-50/60">
                  <Td className="font-mono text-xs text-slate-700">{tenantId === "—" ? "—" : shortId(tenantId)}</Td>
                  <Td>
                    <p className="max-w-md truncate font-semibold text-slate-900">{text(alert.description)}</p>
                    <p className="mt-0.5 font-mono text-xs text-slate-500">{text(alert.reference_number)}</p>
                  </Td>
                  <Td>{humanize(text(alert.source))}</Td>
                  <Td>{alert.created_at ? formatRaised(String(alert.created_at)) : "—"}</Td>
                  <Td>
                    <StatusChip status={text(alert.priority)} />
                  </Td>
                  <Td>
                    <StatusChip status={text(alert.status)} />
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      )}
      <p className="text-sm text-slate-500">
        {visible.length === 0 ? `Showing 0 of ${alerts.length}` : `Showing 1–${visible.length} of ${alerts.length}`}
      </p>
    </div>
  );
}
