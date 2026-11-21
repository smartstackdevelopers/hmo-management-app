import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { Avatar, btnPrimary, btnSecondary, Card, CardHeader, humanize, linkClass, StatusChip } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canGenerateSummary } from "@/lib/caseSummaryView";
import { organisationRequestHeaders } from "@/lib/organisation";
import { canAny } from "@/lib/rbac";
import { TenantTimelinePanel } from "@/components/tenant/TenantTimelinePanel";
import { fetchCaseDetail, type CaseAssignment } from "@/lib/supportApi";
import { requireAuthenticatedSession } from "@/lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap text-sm font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

function shortRef(value: string): string {
  return value.length > 10 ? `…${value.slice(-6)}` : value;
}

export default async function CaseDetailPage({
  params,
}: {
  params: Promise<{ tenantId: string }>;
}) {
  const { tenantId } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/caseload/${tenantId}`);
  const permissions = session.authorization?.permissions;
  if (
    session.authorization &&
    !canAny(permissions, ["support_notes.read.assigned", "tenants.manage", "tenants.read"])
  ) {
    redirect("/unauthorized");
  }

  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return (
      <EmptyState
        title="Choose an organisation"
        description="Select the organisation you're working in to open this case."
      />
    );
  }

  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Case details will be available once sign-in is configured." />;
  }

  try {
    const tokenResult = await auth0.getAccessToken();
    const token = tokenResult?.token;
    if (!token) {
      return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref={`/dashboard/caseload/${tenantId}`} />;
    }
    const detail = await fetchCaseDetail({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      tenantId,
    });
    const canReadTimeline = Boolean(
      permissions &&
        canAny(permissions, [
          "timeline.read",
          "timeline.read.own",
          "timeline.read.landlord",
        ]),
    );
    const canReadVisits = Boolean(
      permissions && canAny(permissions, ["visits.manage.assigned", "tenants.manage"]),
    );
    let caseVisits: { id: string; purpose: string; scheduled_at: string; status: string }[] = [];
    let visitsUnavailable = false;
    if (canReadVisits) {
      try {
        const visitResponse = await fetch(
          `${API_BASE}/api/v1/visits?tenant_id=${encodeURIComponent(tenantId)}&page_size=100`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              ...organisationRequestHeaders({
                organisationId: orgId,
                role: session.authorization?.active_role,
              }),
            },
            cache: "no-store",
          },
        );
        if (!visitResponse.ok) {
          throw new Error(await visitResponse.text());
        }
        const visitPage = (await visitResponse.json()) as {
          items?: { id: string; purpose: string; scheduled_at: string; status: string }[];
        };
        caseVisits = visitPage.items ?? [];
      } catch {
        visitsUnavailable = true;
      }
    }
    const assignments = (detail.assignments ?? []) as CaseAssignment[];
    const latestLog = detail.recent_logs[0];
    const activeAssignment = assignments.find((item) => item.status === "active") ?? assignments[0];
    const workerName = activeAssignment?.support_worker_display_name?.trim() || "";

    const tenant = detail.tenant as {
      preferred_name?: string;
      full_name?: string;
      tenancy_reference?: string;
      email?: string;
      phone?: string;
      needs_goals?: string | null;
      status?: string;
    };
    const name = tenant.preferred_name || tenant.full_name || "Tenant case";
    const pastVisits = caseVisits
      .map((visit) => ({ visit, at: new Date(visit.scheduled_at) }))
      .filter((row) => !Number.isNaN(row.at.getTime()) && row.at.getTime() <= Date.now())
      .sort((left, right) => right.at.getTime() - left.at.getTime());
    const lastVisit = pastVisits[0];
    const lastVisitLabel = !canReadVisits
      ? "—"
      : visitsUnavailable
        ? "Could not be loaded"
        : lastVisit
          ? lastVisit.at.toLocaleDateString("en-GB", { day: "numeric", month: "short" })
          : "—";
    const needsGoals = tenant.needs_goals?.trim() || "";

    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <nav aria-label="Breadcrumb" className="text-sm text-slate-500">
          <span>My work</span>
          <span aria-hidden="true" className="px-1.5">
            /
          </span>
          <Link href="/dashboard/support-worker" className="hover:text-brand-700 hover:underline">
            My caseload
          </Link>
          <span aria-hidden="true" className="px-1.5">
            /
          </span>
          <span className="text-slate-700">{name}</span>
        </nav>

        <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="flex items-start gap-4">
            <Avatar name={name} />
            <div className="min-w-0">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">{name}</h1>
              <p className="mt-1 text-sm text-slate-600">
                {tenant.tenancy_reference ? `Tenancy ${tenant.tenancy_reference}` : "Support notes and handovers for this case"}
              </p>
              {tenant.status || activeAssignment ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {tenant.status ? <StatusChip status={tenant.status} /> : null}
                  {activeAssignment ? <StatusChip status={activeAssignment.status} /> : null}
                </div>
              ) : null}
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Link href={`/dashboard/daily-logs/new?tenantId=${tenantId}`} className={btnPrimary}>
              + Daily log
            </Link>
            <Link href={`/dashboard/visits/new?tenantId=${tenantId}`} className={btnSecondary}>
              Book visit
            </Link>
            <Link href={`/dashboard/handovers/new?tenantId=${tenantId}`} className={btnSecondary}>
              Create handover
            </Link>
            {canGenerateSummary(permissions) ? (
              <Link href={`/dashboard/case-summaries?tenantId=${tenantId}`} className={btnSecondary}>
                Case summary
              </Link>
            ) : null}
          </div>
        </header>

        <nav aria-label="Case sections" className="flex flex-wrap gap-2 border-b border-slate-200">
          {(
            [
              { label: "Overview", href: "#case-overview" },
              { label: "Timeline", href: "#case-timeline" },
              { label: "Support plan", href: `/dashboard/support-plans/tenant?tenantId=${tenantId}` },
              { label: "Daily logs", href: "#case-logs" },
              ...(canReadVisits ? [{ label: "Visits", href: "#case-visits" }] : []),
              { label: "Handovers", href: "#case-handovers" },
            ]
          ).map((section) => (
            <Link
              key={section.label}
              href={section.href}
              aria-current={section.label === "Overview" ? "page" : undefined}
              className={`border-b-2 px-3 py-2 text-sm font-semibold ${
                section.label === "Overview"
                  ? "border-brand-700 text-brand-700"
                  : "border-transparent text-slate-600 hover:text-brand-700"
              }`}
            >
              {section.label}
            </Link>
          ))}
        </nav>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <Card>
              <div id="case-overview">
              <CardHeader title="Overview" />
              <dl className="grid gap-5 sm:grid-cols-3">
                <Fact label="Key worker" value={workerName || "—"} />
                <Fact label="Last visit" value={lastVisitLabel} />
                <Fact label="Latest log" value={latestLog ? latestLog.log_date : "—"} />
                <Fact label="Phone" value={tenant.phone || "—"} />
                <Fact label="Email" value={tenant.email || "—"} />
                <Fact label="Tenancy reference" value={tenant.tenancy_reference || "—"} />
              </dl>
              </div>
            </Card>

            <Card>
              <div id="case-timeline">
              <CardHeader
                title="Activity timeline"
                description="Everything you're allowed to see for this tenant, newest first. Each item links back to its record."
              />
              </div>
              <TenantTimelinePanel
                accessToken={token}
                organisationId={orgId}
                role={session.authorization?.active_role}
                tenantId={tenantId}
                canReadTimeline={canReadTimeline}
              />
            </Card>

            <Card>
              <div id="case-logs">
              <CardHeader title="Recent daily logs" />
              {detail.recent_logs.length === 0 ? (
                <p className="text-sm text-slate-500">No daily logs yet.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {detail.recent_logs.map((log) => (
                    <li key={log.id} className="py-4 first:pt-0 last:pb-0">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-semibold text-slate-900">{log.summary}</p>
                        <StatusChip status={log.status} />
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {log.log_date} · {humanize(log.activity_category)}
                      </p>
                      <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{log.notes}</p>
                    </li>
                  ))}
                </ul>
              )}
              </div>
            </Card>

            {canReadVisits ? (
              <Card>
                <div id="case-visits">
                  <CardHeader title="Visits" description="Scheduled visits already recorded for this case." />
                  {visitsUnavailable ? (
                    <p className="text-sm text-slate-500">Visits could not be loaded.</p>
                  ) : caseVisits.length === 0 ? (
                    <p className="text-sm text-slate-500">No visits recorded for this case.</p>
                  ) : (
                    <ul className="divide-y divide-slate-100">
                      {caseVisits.map((visit) => (
                        <li key={visit.id} className="flex flex-wrap items-center justify-between gap-2 py-4 first:pt-0 last:pb-0">
                          <div>
                            <p className="font-semibold text-slate-900">{visit.purpose}</p>
                            <p className="mt-0.5 text-xs text-slate-500">
                              {new Date(visit.scheduled_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}
                            </p>
                          </div>
                          <StatusChip status={visit.status} />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </Card>
            ) : null}
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader title="Needs and goals" />
              {needsGoals ? (
                <p className="whitespace-pre-wrap text-sm text-slate-700">{needsGoals}</p>
              ) : (
                <p className="text-sm text-slate-500">No needs and goals recorded on this case.</p>
              )}
            </Card>
            <Card>
              <CardHeader title="Assignments" />
              {assignments.length === 0 ? (
                <p className="text-sm text-slate-500">No assignments on this case.</p>
              ) : (
                <ul className="space-y-3">
                  {assignments.map((item) => {
                    const worker = item.support_worker_display_name?.trim() || "";
                    return (
                      <li key={item.id} className="flex items-center gap-3">
                        {worker ? <Avatar name={worker} size="sm" /> : null}
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-slate-900">{worker || shortRef(item.support_worker_user_id)}</p>
                          <p className="text-xs text-slate-500">
                            {new Date(item.assigned_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                          </p>
                        </div>
                        <StatusChip status={item.status} />
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
            <Card>
              <div id="case-handovers">
              <CardHeader title="Recent handovers" />
              {detail.recent_handovers.length === 0 ? (
                <p className="text-sm text-slate-500">No handovers yet.</p>
              ) : (
                <ul className="space-y-4">
                  {detail.recent_handovers.map((item) => (
                    <li key={item.id} className="rounded-xl border border-slate-100 p-3">
                      <p className="text-sm font-semibold text-slate-900">{item.summary}</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        <StatusChip status={item.status} />
                        <StatusChip status={item.priority} />
                      </div>
                      <p className="mt-2 text-xs text-slate-500">
                        {new Date(item.handover_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}
                      </p>
                      <Link href={`/dashboard/handovers/${item.id}`} className={`${linkClass} mt-2 inline-block text-sm`}>
                        View handover
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              </div>
            </Card>
            <Link href="/dashboard/support-worker" className={`${linkClass} inline-block text-sm`}>
              My caseload
            </Link>
          </div>
        </div>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "We couldn't load this case. Please try again."}
        retryHref={`/dashboard/caseload/${tenantId}`}
      />
    );
  }
}