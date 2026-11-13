import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { getSafeguardingDashboard, listSafeguardingAlerts } from "@/lib/safeguardingAlertsApi";

const READ = ["safeguarding_alerts.read", "safeguarding_alerts.manage"];

export default async function SafeguardingAlertsPage() {
  const session = await requireAuthenticatedSession("/dashboard/safeguarding-alerts");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  let stats: Record<string, unknown> = {};
  let alerts: Record<string, unknown>[] = [];
  try {
    stats = await getSafeguardingDashboard(token, orgId);
    alerts = await listSafeguardingAlerts(token, orgId);
  } catch {
    return (
      <ErrorState description="Safeguarding alerts add-on is disabled until SAFEGUARDING_ALERTS_GLOBAL_ENABLED and organisation settings are approved." />
    );
  }
  const byStatus = (stats.by_status ?? {}) as Record<string, number>;
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Safeguarding alerts (add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Early-warning suggestions require human review. This system does not determine abuse, neglect, or safety
          outcomes.
        </p>
      </header>
      <section className="grid gap-4 sm:grid-cols-4">
        <Stat label="Total alerts" value={String(stats.total_alerts ?? "0")} />
        <Stat label="Critical open" value={String(stats.critical_open ?? "0")} />
        <Stat label="Overdue follow-ups" value={String(stats.overdue_follow_ups ?? "0")} />
        <Stat label="New" value={String(byStatus.new ?? "0")} />
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="font-medium text-slate-800">Recent alerts</h2>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {alerts.length === 0 ? (
            <li className="py-2 text-slate-500">No alerts recorded.</li>
          ) : (
            alerts.slice(0, 25).map((a) => (
              <li key={String(a.id)} className="flex justify-between py-2">
                <span>
                  {String(a.reference_number)} — {String(a.priority)} / {String(a.status)}
                </span>
                <span className="text-slate-500">{String(a.created_at ?? "")}</span>
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}
