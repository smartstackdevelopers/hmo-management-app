import Link from "next/link";
import { redirect } from "next/navigation";
import { MaintenanceActions } from "@/components/maintenance/MaintenanceActions";
import { EmergencyInstructionsPanel } from "@/components/maintenance/EmergencyInstructionsPanel";
import { MaintenancePhotoGallery } from "@/components/maintenance/MaintenancePhotoGallery";
import { PriorityChip } from "@/components/maintenance/PriorityChip";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader, StatusChip, humanize, linkClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  fetchEmergencyContent,
  fetchMaintenanceRequest,
  isEmergencyRequest,
  listMaintenanceFiles,
  listMaintenanceHistory,
  listMaintenanceNotes,
  listMaintenanceVisits,
} from "@/lib/maintenanceApi";
import { can, canAny, isApprovedRole } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function MaintenanceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/maintenance/${id}`);
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "maintenance.manage",
      "maintenance.read.own",
      "maintenance.read.assigned",
      "maintenance.read.property",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select an organisation to see this repair." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in unavailable" description="We can't load this repair right now. Please try again later." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState title="Session expired" description="Please sign in again to see this repair." />;
    const role = session.authorization?.active_role;
    const permissions = session.authorization?.permissions ?? [];
    const activeRole = role && isApprovedRole(role) ? role : null;
    const isTenant = activeRole === "tenant";
    const isContractor = activeRole === "maintenance_contractor";

    const [request, history, notes, visits, files] = await Promise.all([
      fetchMaintenanceRequest({ accessToken: token, organisationId: orgId, role, requestId: id }),
      listMaintenanceHistory({ accessToken: token, organisationId: orgId, role, requestId: id }),
      listMaintenanceNotes({ accessToken: token, organisationId: orgId, role, requestId: id }),
      listMaintenanceVisits({ accessToken: token, organisationId: orgId, role, requestId: id }),
      listMaintenanceFiles({ accessToken: token, organisationId: orgId, role, requestId: id }),
    ]);

    const showEmergency = request.show_emergency_panel || Boolean(request.emergency_kind_hint);
    let gasContent = null;
    let fireContent = null;
    if (showEmergency) {
      [gasContent, fireContent] = await Promise.all([
        fetchEmergencyContent({ accessToken: token, organisationId: orgId, role, kind: "gas" }).catch(() => null),
        fetchEmergencyContent({ accessToken: token, organisationId: orgId, role, kind: "fire" }).catch(() => null),
      ]);
    }

    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <Link href="/dashboard/maintenance" className={`text-sm ${linkClass}`}>
          ← Back to repairs
        </Link>
        <PageHeader
          eyebrow={`Operations / Maintenance / ${request.reference_number}`}
          title={request.title}
          description={[humanize(request.category_code), request.reference_number].filter(Boolean).join(" · ")}
        />
        <div className="-mt-4 flex flex-wrap gap-2">
          <StatusChip status={request.status} />
          <PriorityChip priority={request.priority} />
          {isEmergencyRequest(request) ? <StatusChip tone="red">Emergency</StatusChip> : null}
          {request.requires_approval ? (
            <StatusChip tone="amber">Approval: {request.approval_status ? humanize(request.approval_status) : "Not yet decided"}</StatusChip>
          ) : null}
        </div>

        {showEmergency ? (
          <div className="grid gap-4 md:grid-cols-2">
            {gasContent ? <EmergencyInstructionsPanel kind="gas" content={gasContent} /> : null}
            {fireContent ? <EmergencyInstructionsPanel kind="fire" content={fireContent} /> : null}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <Card>
              <CardHeader title="Details" />
              <dl className="grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Reported</dt>
                  <dd className="mt-0.5 font-semibold text-slate-900">{new Date(request.reported_at).toLocaleString("en-GB")}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Scheduled visit</dt>
                  <dd className="mt-0.5 font-semibold text-slate-900">
                    {request.scheduled_visit_at
                      ? new Date(request.scheduled_visit_at).toLocaleString("en-GB", { timeZone: request.visit_timezone })
                      : "Not booked yet"}
                  </dd>
                </div>
              </dl>
              <div className="mt-5 border-t border-slate-100 pt-4">
                <p className="text-sm font-medium text-slate-500">Description</p>
                <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">{request.description}</p>
              </div>
            </Card>

            <Card>
              <CardHeader title="Photos" />
              <MaintenancePhotoGallery
                requestId={request.id}
                files={files}
                accessToken={token}
                organisationId={orgId}
                role={role}
              />
            </Card>

            <Card>
              <CardHeader title="Activity" />
              {history.length === 0 ? (
                <p className="text-sm text-slate-500">No activity yet.</p>
              ) : (
                <ol className="space-y-4">
                  {history.map((event, index) => (
                    <li key={event.id} className="relative flex gap-3">
                      <span className="flex flex-col items-center">
                        <span aria-hidden="true" className={`mt-1 h-2.5 w-2.5 rounded-full ${index === 0 ? "bg-brand-600" : "bg-slate-300"}`} />
                        {index < history.length - 1 ? <span aria-hidden="true" className="mt-1 w-px flex-1 bg-slate-200" /> : null}
                      </span>
                      <div className="min-w-0 flex-1 pb-1">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <p className="text-sm font-semibold text-slate-900">{event.summary}</p>
                          <p className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString("en-GB")}</p>
                        </div>
                        {event.detail ? <p className="mt-0.5 text-sm text-slate-600">{event.detail}</p> : null}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader title="Actions" />
              <MaintenanceActions
                requestId={request.id}
                status={request.status}
                accessToken={token}
                organisationId={orgId}
                role={role}
                canManage={can(permissions, "maintenance.manage")}
                canAssign={can(permissions, "maintenance.assign")}
                canPriority={can(permissions, "maintenance.priority.manage")}
                canSchedule={can(permissions, "maintenance.schedule")}
                canApprove={can(permissions, "maintenance.approve")}
                canNotes={canAny(permissions, ["maintenance.notes.add", "maintenance.manage"])}
                canComplete={can(permissions, "maintenance.complete")}
                canUploadPhoto={can(permissions, "maintenance.photo.upload")}
                isTenant={isTenant}
                isContractor={isContractor}
              />
            </Card>

            <Card>
              <CardHeader title="Visits" />
              {visits.length === 0 ? (
                <p className="text-sm text-slate-500">No visits booked yet.</p>
              ) : (
                <ul className="space-y-3 text-sm">
                  {visits.map((v) => (
                    <li key={v.id} className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-semibold text-slate-900">{new Date(v.scheduled_at).toLocaleString("en-GB")}</p>
                        <StatusChip status={v.status} />
                      </div>
                      {v.work_notes ? <p className="mt-1 text-slate-600">{v.work_notes}</p> : null}
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title="Notes" />
              {notes.length === 0 ? (
                <p className="text-sm text-slate-500">No notes yet.</p>
              ) : (
                <ul className="space-y-3 text-sm">
                  {notes.map((note) => (
                    <li key={note.id} className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
                      <p className="text-xs font-semibold text-slate-500">{humanize(note.visibility)}</p>
                      <p className="mt-1 whitespace-pre-wrap text-slate-700">{note.body}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "We couldn't load this repair."}
        retryHref={`/dashboard/maintenance/${id}`}
      />
    );
  }
}
