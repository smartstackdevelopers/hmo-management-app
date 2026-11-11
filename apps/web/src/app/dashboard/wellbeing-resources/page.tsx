import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { WellbeingResourceAdminForm } from "./WellbeingResourceAdminForm";

export default async function WellbeingResourcesPage() {
  const session = await requireAuthenticatedSession("/dashboard/wellbeing-resources");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["wellbeing.resources.manage", "tenants.manage"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot manage wellbeing resources." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Access token unavailable" description="Sign in again." />;
  }
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow="F5.5"
        title="Wellbeing resources"
        description="Manage exercise, mindfulness and local wellbeing directory listings. Private tenant mood check-ins are not shown here."
      />
      <p className="text-sm text-slate-600">
        HMore wellbeing tools are non-clinical. Do not present resources as medical treatment.
      </p>
      <WellbeingResourceAdminForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
      />
    </div>
  );
}
