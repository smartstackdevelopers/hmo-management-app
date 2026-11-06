import Link from "next/link";
import { redirect } from "next/navigation";
import { MaintenanceActions } from "@/components/maintenance/MaintenanceActions";
import { EmergencyInstructionsPanel } from "@/components/maintenance/EmergencyInstructionsPanel";
import { MaintenancePhotoGallery } from "@/components/maintenance/MaintenancePhotoGallery";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  fetchEmergencyContent,
  fetchMaintenanceRequest,
  isEmergencyRequest,
  listMaintenanceFiles,
  listMaintenanceHistory,
  listMaintenanceNotes,
  listMaintenanceVisits,
  maintenancePriorityBadgeClass,
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
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load maintenance request." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
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
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow={request.reference_number}
          title={request.title}
          description={`${request.status.replaceAll("_", " ")} · category ${request.category_code}`}
        />
        <div className="flex flex-wrap gap-2">
          <span className={`rounded border px-2 py-0.5 text-xs uppercase ${maintenancePriorityBadgeClass(request.priority)}`}>
            {request.priority}
          </span>
          {isEmergencyRequest(request) ? (
            <span className="rounded border border-red-500 bg-red-50 px-2 py-0.5 text-xs font-semibold uppercase text-red-950">
              Emergency priority
            </span>
          ) : null}
          {request.requires_approval ? (
            <span className="rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs text-amber-950">
              Approval: {request.approval_status ?? "n/a"}
            </span>
          ) : null}
        </div>
        <p className="whitespace-pre-wrap text-sm text-slate-700">{request.description}</p>

        {showEmergency ? (
          <div className="grid gap-3 md:grid-cols-2">
            {gasContent ? <EmergencyInstructionsPanel kind="gas" content={gasContent} /> : null}
            {fireContent ? <EmergencyInstructionsPanel kind="fire" content={fireContent} /> : null}
          </div>
        ) : null}

        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Reported</dt>
            <dd>{new Date(request.reported_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Scheduled visit</dt>
            <dd>
              {request.scheduled_visit_at
                ? new Date(request.scheduled_visit_at).toLocaleString(undefined, { timeZone: request.visit_timezone })
                : "—"}
            </dd>
          </div>
        </dl>

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

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Visits</h2>
          {visits.length === 0 ? (
            <p className="text-sm text-slate-500">No visits recorded.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {visits.map((v) => (
                <li key={v.id} className="rounded border border-slate-200 p-3">
                  <p className="font-mono text-xs text-slate-500">{v.id}</p>
                  <p>
                    {new Date(v.scheduled_at).toLocaleString()} · {v.status}
                  </p>
                  {v.work_notes ? <p className="text-slate-700">{v.work_notes}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Photographs</h2>
          <MaintenancePhotoGallery
            requestId={request.id}
            files={files}
            accessToken={token}
            organisationId={orgId}
            role={role}
          />
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Notes</h2>
          {notes.length === 0 ? (
            <p className="text-sm text-slate-500">No visible notes.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {notes.map((note) => (
                <li key={note.id} className="rounded border border-slate-200 p-3">
                  <p className="text-xs uppercase text-slate-500">{note.visibility.replaceAll("_", " ")}</p>
                  <p className="whitespace-pre-wrap">{note.body}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">History</h2>
          {history.length === 0 ? (
            <p className="text-sm text-slate-500">No history yet.</p>
          ) : (
            <ol className="relative space-y-3 border-l border-slate-200 pl-4 text-sm">
              {history.map((event) => (
                <li key={event.id} className="ml-1">
                  <p className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</p>
                  <p className="font-medium">{event.summary}</p>
                  {event.detail ? <p className="text-slate-700">{event.detail}</p> : null}
                </li>
              ))}
            </ol>
          )}
        </section>

        <Link href="/dashboard/maintenance" className="text-sm text-teal-800 hover:underline">
          ← Back to maintenance
        </Link>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load maintenance request."}
      />
    );
  }
}
