import Link from "next/link";
import { redirect } from "next/navigation";
import { ComplaintActions } from "@/components/complaints/ComplaintActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  fetchComplaint,
  listComplaintHistory,
  listComplaintNotes,
  priorityBadgeClass,
} from "@/lib/complaintsApi";
import { can, canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function ComplaintDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
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
      fetchComplaint({ accessToken: token, organisationId: orgId, role, complaintId: id }),
      listComplaintHistory({ accessToken: token, organisationId: orgId, role, complaintId: id }),
      listComplaintNotes({ accessToken: token, organisationId: orgId, role, complaintId: id }),
    ]);
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow={complaint.reference_number}
          title={complaint.title}
          description={`${complaint.status.replaceAll("_", " ")} · priority ${complaint.priority}`}
        />
        <div className="flex flex-wrap gap-2">
          <span className={`rounded border px-2 py-0.5 text-xs uppercase ${priorityBadgeClass(complaint.priority)}`}>
            {complaint.priority}
          </span>
          {complaint.is_overdue ? (
            <span className="rounded border border-red-300 bg-red-50 px-2 py-0.5 text-xs text-red-900">
              Overdue
            </span>
          ) : null}
          {complaint.open_escalation ? (
            <span className="rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs text-amber-950">
              Escalation open
            </span>
          ) : null}
        </div>
        <p className="whitespace-pre-wrap text-sm text-slate-700">{complaint.description}</p>
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Acknowledge due</dt>
            <dd>{complaint.acknowledge_due_at ? new Date(complaint.acknowledge_due_at).toLocaleString() : "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Response due</dt>
            <dd>{complaint.response_due_at ? new Date(complaint.response_due_at).toLocaleString() : "—"}</dd>
          </div>
        </dl>
        {complaint.tenant_visible_summary ? (
          <p className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-950">
            Summary: {complaint.tenant_visible_summary}
          </p>
        ) : null}
        {complaint.resolution_summary ? (
          <p className="rounded border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800">
            Internal resolution: {complaint.resolution_summary}
          </p>
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
          canEscalate={can(permissions, "complaints.escalate")}
          canClose={can(permissions, "complaints.close")}
          canNotes={canAny(permissions, ["complaints.notes.add", "complaints.manage"])}
          canDeadlines={can(permissions, "complaints.deadlines.manage")}
        />

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Notes</h2>
          {notes.length === 0 ? (
            <p className="text-sm text-slate-500">No visible notes.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {notes.map((note) => (
                <li key={note.id} className="rounded border border-slate-200 p-3">
                  <p className="text-xs uppercase text-slate-500">
                    {note.visibility.replaceAll("_", " ")}
                    {note.is_follow_up ? " · follow-up" : ""}
                  </p>
                  <p className="whitespace-pre-wrap">{note.body}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">History</h2>
          <ol className="space-y-2 border-l border-slate-200 pl-4 text-sm">
            {history.map((event) => (
              <li key={event.id}>
                <p className="font-medium text-slate-900">{event.summary}</p>
                <p className="text-xs text-slate-500">
                  {event.event_type} · {new Date(event.created_at).toLocaleString()}
                </p>
                {event.detail ? <p className="text-slate-600">{event.detail}</p> : null}
              </li>
            ))}
          </ol>
        </section>

        <Link href="/dashboard/complaints" className="text-sm text-teal-800 hover:underline">
          Back to complaints
        </Link>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load complaint."}
      />
    );
  }
}
