import { redirect } from "next/navigation";
import { CommunityServiceForm } from "@/components/community/CommunityServiceForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { getAdminCommunityService } from "@/lib/communityDirectoryApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function EditCommunityServicePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/community-directory");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "organisations.manage",
      "organisation.settings.manage",
    ]) &&
    session.authorization.active_role !== "organisation_admin" &&
    session.authorization.active_role !== "super_admin"
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot edit listing." />;
  }
  const { id } = await params;
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const service = await getAdminCommunityService({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      serviceId: id,
    });
    return (
      <div className="mx-auto max-w-xl space-y-6">
        <PageHeader
          eyebrow="F5.1"
          title={`Edit ${service.name}`}
          description="Editing verified content moves the listing to needs review."
        />
        <CommunityServiceForm
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          existing={service}
        />
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load listing."} />
    );
  }
}
