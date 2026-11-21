import Link from "next/link";
import { redirect } from "next/navigation";
import { ApplicationReviewActions } from "@/components/housing/ApplicationReviewActions";
import { EvidencePanel } from "@/components/housing/EvidencePanel";
import { HousingApplicationAnalysisPanel } from "@/components/housing/HousingApplicationAnalysisPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, StatusChip, linkClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchApplication } from "@/lib/housingApi";
import { canRunHousingApplicationAnalysis } from "@/lib/housingApplicationAnalysisView";
import { can, canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function HousingApplicationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/housing-applications/${id}`);
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "applications.manage",
      "applications.review",
      "applications.read.own",
      "applications.read.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
    const app = await fetchApplication({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      applicationId: id,
    });
    const permissions = session.authorization?.permissions;
    const canReview = canAny(permissions, ["applications.review", "applications.manage"]);
    const canEvidenceManage = canAny(permissions, [
      "evidence.manage",
      "evidence.manage.assigned",
    ]);
    const canEvidenceReview = can(permissions, "evidence.review");
    const canGeneratePack = can(permissions, "evidence.pack.generate");
    const canViewEvidence = canAny(permissions, [
      "evidence.manage",
      "evidence.manage.assigned",
      "evidence.read.assigned",
      "evidence.read.own",
      "evidence.review",
      "evidence.pack.generate",
    ]);
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <Link href="/dashboard/housing-applications" className={`text-sm ${linkClass}`}>
          ← Back to applications
        </Link>
        <PageHeader
          eyebrow={app.reference_number}
          title="Housing application"
          description={
            app.on_waiting_list
              ? `Waiting list position ${app.waiting_list_position}. Position does not guarantee allocation.`
              : "Review the housing requirements and record a decision."
          }
        />
        <div className="flex flex-wrap gap-2">
          <StatusChip status={app.status} />
          <StatusChip status={app.priority} />
          {app.on_waiting_list ? <StatusChip tone="blue">Waiting list #{app.waiting_list_position}</StatusChip> : null}
        </div>
        <Card>
          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{app.housing_requirements}</p>
        </Card>
        {app.information_required_notes ? (
          <p className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            Information required: {app.information_required_notes}
          </p>
        ) : null}
        <ApplicationReviewActions
          applicationId={app.id}
          status={app.status}
          onWaitingList={app.on_waiting_list}
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          canReview={canReview}
        />
        {canRunHousingApplicationAnalysis(permissions) ? (
          <HousingApplicationAnalysisPanel
            applicationId={app.id}
            accessToken={token}
            organisationId={orgId}
            role={session.authorization?.active_role}
            permissions={permissions ?? []}
          />
        ) : null}
        {canViewEvidence ? (
          <EvidencePanel
            applicationId={app.id}
            accessToken={token}
            organisationId={orgId}
            role={session.authorization?.active_role}
            canManage={canEvidenceManage}
            canReview={Boolean(canEvidenceReview)}
            canGeneratePack={Boolean(canGeneratePack)}
          />
        ) : null}
      </div>
    );
  } catch {
    return (
      <ErrorState
        description={"Failed to load application."}
      />
    );
  }
}
