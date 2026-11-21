import { redirect } from "next/navigation";
import { CommunityServiceForm } from "@/components/community/CommunityServiceForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewCommunityServicePage() {
  const session = await requireAuthenticatedSession("/dashboard/community-directory/new");
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
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Sign in again" description="Sign in again." />;
  }
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Community / Directory"
        title="Add community service"
        description="Tenants see published services in Help Near Me. Leave a field blank when you don't know it."
      />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <CommunityServiceForm
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
        />
        <Card>
          <CardHeader title="Guidance" />
          <ul className="space-y-3 text-sm text-slate-600">
            <li>Check details with the provider before publishing.</li>
            <li>Use plain English. Tenants read this.</li>
            <li>New listings start as pending verification and are never auto-verified.</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
