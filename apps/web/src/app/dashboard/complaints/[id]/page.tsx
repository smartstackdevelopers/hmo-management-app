import Link from "next/link";
import { redirect } from "next/navigation";
import { ComplaintActions } from "@/components/complaints/ComplaintActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { Card, CardHeader, StatusChip, btnPrimary, btnSecondary, humanize, linkClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchComplaint, listComplaintHistory, listComplaintNotes, type Complaint } from "@/lib/complaintsApi";
import { organisationRequestHeaders } from "@/lib/organisation";
import { can, canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ComplaintDetail = Complaint & {
  acknowledged_at?: string | null;
  property_id?: string | null;
};

function formatDay(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

const INVESTIGATED = new Set([
  "investigation",
  "awaiting_information",
  "escalated",
  "resolved",
  "closed",
  "reopened",
]);

export default async function ComplaintDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const session = await requireAuthenticatedSession(`/dashboard/complaints/${id}`);
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "complaints.manage",
      "complaints.read.own",
      "complaints.read.assigned",
      "complaints.read.property",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load complaint." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const role = session.authorization?.active_role;
    const permissions = session.authorization?.permissions;
    const [complaint, history, notes] = await Promise.all([
      fetchComplaint({ accessToken: token, organisationId: orgId, role, complaintId: id }) as Promise<ComplaintDetail>,
      listComplaintHistory({ accessToken: token, organisationId: orgId, role, complaintId: id }),
      listComplaintNotes({ accessToken: token, organisationId: orgId, role, complaintId: id }),
    ]);
    let propertyName: string | null = null;
    if (complaint.property_id && canAny(permissions, ["properties.read", "properties.manage"])) {
      try {
        const response = await fetch(`${API_BASE}/api/v1/properties/${complaint.property_id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            ...organisationRequestHeaders({ organisationId: orgId, role }),
          },
          cache: "no-store",
        });
        if (response.ok) {
          const property = (await response.json()) as { name?: string };
          propertyName = property.name ?? null;
        }
      } catch {
        propertyName = null;
      }
    }

    const raised = formatDay(complaint.submitted_at);
    const responseDue = formatDay(complaint.response_due_at);
    const acknowledged = Boolean(complaint.acknowledged_at);
    const investigated = INVESTIGATED.has(complaint.status);
    const responded = Boolean(complaint.tenant_visible_summary);
    const closedOrEscalated =
      complaint.open_escalation ||
      complaint.status === "escalated" ||
      complaint.status === "resolved" ||
      complaint.status === "closed";
    const steps = [
      { label: "Acknowledge", done: acknowledged },
      { label: "Investigate", done: investigated },
      { label: "Respond in writing", done: responded },
      { label: "Close or escalate", done: closedOrEscalated },
    ];
    const canRespond = canAny(permissions, [
      "complaints.manage",
      "complaints.close",
      "complaints.notes.add",
      "complaints.escalate",
    ]);
    const canEscalate = can(permissions, "complaints.escalate");
    const tabs = [
      { id: "overview", label: "Overview" },
      { id: "timeline", label: "Timeline" },
      { id: "evidence", label: "Evidence" },
      { id: "response", label: "Response" },
    ];
    const tab = tabs.some((item) => item.id === query.tab) ? query.tab! : "overview";
    const tabHref = (next: string) =>
      next === "overview" ? `/dashboard/complaints/${id}` : `/dashboard/complaints/${id}?tab=${next}`;
    const subtitle = [humanize(complaint.category_code), propertyName, raised ? `Raised ${raised}` : null]
      .filter(Boolean)
      .join(" · ");

    const timeline = (
      <Card>
        <CardHeader title="Activity timeline" />
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">No activity yet.</p>
        ) : (
          <ol className="space-y-4">
            {history.map((event, index) => (
              <li key={event.id} className="relative flex gap-3">
                <span className="flex flex-col items-center">
                  <span
                    aria-hidden="true"
                    className={`mt-1.5 h-2.5 w-2.5 rounded-full ${index === 0 ? "bg-brand-600" : "bg-slate-300"}`}
                  />
                  {index < history.length - 1 ? <span aria-hidden="true" className="mt-1 w-px flex-1 bg-slate-200" /> : null}
                </span>
                <div className="min-w-0 flex-1 pb-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-900">{event.summary}</p>
                    <p className="text-xs text-slate-500">{formatDay(event.created_at) ?? event.created_at}</p>
                  </div>
                  {event.detail ? <p className="mt-0.5 text-sm text-slate-600">{event.detail}</p> : null}
                </div>
              </li>
            ))}
          </ol>
        )}
      </Card>
    );

    return (
      <div className="mx-auto max-w-6xl space-y-5">
        <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">
              Operations / Complaints / {complaint.reference_number}
            </p>
            <div className="mt-2 flex items-center gap-3">
              <span
                aria-hidden="true"
                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-700"
              >
                <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M7 3.5h7l5 5V20a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z" strokeLinejoin="round" />
                  <path d="M14 3.5V9h5.5M8.5 13h7M8.5 17h5" strokeLinecap="round" />
                </svg>
              </span>
              <div className="min-w-0">
                <h1 className="truncate text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">
                  {complaint.reference_number} · {complaint.title}
                </h1>
                {subtitle ? <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p> : null}
              </div>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {canRespond ? (
              <Link
                href={`/dashboard/complaints/${id}?tab=response`}
                className={tab === "response" ? btnSecondary : btnPrimary}
              >
                Respond
              </Link>
            ) : null}
            {canEscalate ? (
              <Link href={`/dashboard/complaints/${id}?tab=response#escalate`} className={btnSecondary}>
                Escalate
              </Link>
            ) : null}
          </div>
        </header>
        <div className="flex flex-wrap gap-2">
          <StatusChip status={complaint.status} />
          <StatusChip status={complaint.priority} />
          {responseDue ? (
            <StatusChip tone={complaint.is_overdue ? "red" : "amber"}>Response due {responseDue}</StatusChip>
          ) : null}
          {complaint.open_escalation ? <StatusChip tone="amber">Escalation open</StatusChip> : null}
        </div>

        <nav aria-label="Complaint sections" className="flex gap-5 border-b border-slate-200">
          {tabs.map((item) => (
            <Link
              key={item.id}
              href={tabHref(item.id)}
              aria-current={tab === item.id ? "page" : undefined}
              className={`-mb-px border-b-2 pb-2 text-sm font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
                tab === item.id ? "border-brand-700 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            {tab === "overview" || tab === "timeline" ? (
              tab === "overview" ? (
                <>
                  <Card>
                    <CardHeader title="Overview" />
                    <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{complaint.description}</p>
                    <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3">
                      <div>
                        <dt className="text-slate-500">Category</dt>
                        <dd className="mt-0.5 font-semibold text-slate-900">{humanize(complaint.category_code)}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">Raised</dt>
                        <dd className="mt-0.5 font-semibold text-slate-900">{raised ?? "—"}</dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">Assignment</dt>
                        <dd className="mt-0.5 font-semibold text-slate-900">
                          {complaint.assigned_user_id ? "Assigned" : "Unassigned"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">Response due</dt>
                        <dd className="mt-0.5 font-semibold text-slate-900">{responseDue ?? "—"}</dd>
                      </div>
                      {propertyName ? (
                        <div>
                          <dt className="text-slate-500">Property</dt>
                          <dd className="mt-0.5 font-semibold text-slate-900">{propertyName}</dd>
                        </div>
                      ) : null}
                      {complaint.file_ids?.length > 0 ? (
                        <div>
                          <dt className="text-slate-500">Files</dt>
                          <dd className="mt-0.5 font-semibold text-slate-900">{complaint.file_ids.length}</dd>
                        </div>
                      ) : null}
                    </dl>
                  </Card>
                  {timeline}
                </>
              ) : (
                timeline
              )
            ) : null}

            {tab === "evidence" ? (
              <Card>
                <CardHeader title="Evidence" description="Notes and files recorded on this complaint." />
                {complaint.file_ids?.length > 0 ? (
                  <p className="mb-4 text-sm text-slate-600">{complaint.file_ids.length} file(s) linked.</p>
                ) : null}
                {notes.length === 0 ? (
                  <p className="text-sm text-slate-500">No visible notes.</p>
                ) : (
                  <ul className="space-y-3 text-sm">
                    {notes.map((note) => (
                      <li key={note.id} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {note.visibility.replaceAll("_", " ")}
                          {note.is_follow_up ? " · follow-up" : ""}
                        </p>
                        <p className="mt-1 whitespace-pre-wrap text-slate-800">{note.body}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            ) : null}

            {tab === "response" ? (
              <>
                {complaint.tenant_visible_summary ? (
                  <Card className="border-emerald-200 bg-emerald-50">
                    <CardHeader title="Tenant-visible summary" />
                    <p className="text-sm text-emerald-950">{complaint.tenant_visible_summary}</p>
                  </Card>
                ) : null}
                {complaint.resolution_summary ? (
                  <Card>
                    <CardHeader title="Internal resolution" />
                    <p className="text-sm text-slate-800">{complaint.resolution_summary}</p>
                  </Card>
                ) : null}
                <ComplaintActions
                  complaintId={complaint.id}
                  status={complaint.status}
                  accessToken={token}
                  organisationId={orgId}
                  role={role}
                  canManage={can(permissions, "complaints.manage")}
                  canAssign={can(permissions, "complaints.assign")}
                  canPriority={can(permissions, "complaints.priority.manage")}
                  canEscalate={canEscalate}
                  canClose={can(permissions, "complaints.close")}
                  canNotes={canAny(permissions, ["complaints.notes.add", "complaints.manage"])}
                  canDeadlines={can(permissions, "complaints.deadlines.manage")}
                />
              </>
            ) : null}
          </div>

          <Card>
            <CardHeader title="Resolution steps" />
            <ul className="space-y-3">
              {steps.map((step) => (
                <li key={step.label} className="flex items-center gap-3 text-sm text-slate-800">
                  <input type="checkbox" defaultChecked={step.done} disabled className="h-4 w-4 rounded border-slate-300" />
                  <span>{step.label}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
        <p className="text-sm">
          <Link href="/dashboard/complaints" className={linkClass}>
            Back to complaints
          </Link>
        </p>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load complaint."} />
    );
  }
}
