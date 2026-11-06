import { redirect } from "next/navigation";
import { ComplaintForm } from "@/components/complaints/ComplaintForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewComplaintPage() {
  const session = await requireAuthenticatedSession("/dashboard/complaints/new");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "complaints.manage",
      "complaints.create.own",
      "complaints.create.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot submit complaint." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Access token unavailable" description="Sign in again." />;
  }
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        eyebrow="Complaints"
        title="Submit complaint"
        description="Submit an organisation-scoped complaint. Deadlines are operational targets, not statutory."
      />
      <ComplaintForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
      />
    </div>
  );
}
