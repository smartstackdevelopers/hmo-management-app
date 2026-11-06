import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { VisitForm } from "@/components/ops/VisitForm";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewVisitPage() {
  const session = await requireAuthenticatedSession("/dashboard/visits/new");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["visits.manage.assigned", "tenants.manage"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot schedule visits." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader eyebrow="Visits" title="Schedule visit" description="Support Workers may only assign visits to themselves for caseload tenants." />
      <VisitForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
        defaultStaffUserId={session.authorization?.user_id}
      />
    </div>
  );
}
