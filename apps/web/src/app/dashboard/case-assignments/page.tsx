import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { AssignmentForm } from "@/components/support/AssignmentForm";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function CaseAssignmentsPage() {
  const session = await requireAuthenticatedSession("/dashboard/case-assignments");
  if (session.authorization && !can(session.authorization.permissions, "tenants.manage")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot manage assignments." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        eyebrow="Organisation"
        title="Case assignments"
        description="Assign Support Workers to tenant person records. Workers cannot self-assign."
      />
      <AssignmentForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
      />
    </div>
  );
}
