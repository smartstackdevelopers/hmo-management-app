import Link from "next/link";
import { redirect } from "next/navigation";
import { FollowUpCompleteButton } from "@/components/incidents/FollowUpCompleteButton";
import { IncidentActions } from "@/components/incidents/IncidentActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchIncident, fetchIncidentFollowUps } from "@/lib/incidentsApi";
import { can, canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function IncidentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/incidents/${id}`);
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "incidents.manage",
      "incidents.read.assigned",
      "incidents.create.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load incident." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const [incident, followUps] = await Promise.all([
      fetchIncident({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization?.active_role,
        incidentId: id,
      }),
      fetchIncidentFollowUps({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization?.active_role,
        incidentId: id,
      }),
    ]);
    const canManage = can(session.authorization?.permissions, "incidents.manage");
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow={incident.reference_number}
          title={incident.title}
          description={`${incident.status} · ${incident.severity} · ${incident.category}`}
        />
        <p className="text-sm text-slate-700 whitespace-pre-wrap">{incident.description}</p>
        <IncidentActions
          incidentId={incident.id}
          status={incident.status}
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          canManage={canManage}
        />
        <section className="space-y-3">
          <h2 className="text-base font-medium text-forest-900">Follow-ups</h2>
          {followUps.items.length === 0 ? (
            <EmptyState title="No follow-ups" description="Add actions to track resolution work." />
          ) : (
            <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
              {followUps.items.map((row) => (
                <li key={row.id} className="flex items-start justify-between gap-3 p-4 text-sm">
                  <div>
                    <p className="font-medium text-forest-900">{row.description}</p>
                    <p className="text-slate-600">
                      {row.status} · {row.priority}
                      {row.due_at ? ` · due ${new Date(row.due_at).toLocaleString()}` : ""}
                    </p>
                  </div>
                  <FollowUpCompleteButton
                    followUpId={row.id}
                    status={row.status}
                    accessToken={token}
                    organisationId={orgId}
                    role={session.authorization?.active_role}
                  />
                </li>
              ))}
            </ul>
          )}
        </section>
        <Link href="/dashboard/incidents" className="text-sm text-teal-800 hover:underline">
          Back to incidents
        </Link>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load incident."} />
    );
  }
}
