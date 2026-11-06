import Link from "next/link";
import { redirect } from "next/navigation";
import { ApplicationReviewActions } from "@/components/housing/ApplicationReviewActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchApplication } from "@/lib/housingApi";
import { canAny } from "@/lib/rbac";
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
    return <EmptyState title="Auth0 not configured" description="Cannot load application." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const app = await fetchApplication({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      applicationId: id,
    });
    const canReview = canAny(session.authorization?.permissions, [
      "applications.review",
      "applications.manage",
    ]);
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow={app.reference_number}
          title={`Application · ${app.status}`}
          description={`Priority ${app.priority}${
            app.on_waiting_list ? ` · waiting list position ${app.waiting_list_position}` : ""
          }`}
        />
        <p className="whitespace-pre-wrap text-sm text-slate-700">{app.housing_requirements}</p>
        {app.information_required_notes ? (
          <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
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
        <Link href="/dashboard/housing-applications" className="text-sm text-teal-800 hover:underline">
          Back to applications
        </Link>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load application."}
      />
    );
  }
}
