import { redirect } from "next/navigation";
import { SafeguardingForm } from "@/components/compliance/SafeguardingForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewSafeguardingPage() {
  const session = await requireAuthenticatedSession("/dashboard/safeguarding/new");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "safeguarding.reminders.manage",
      "safeguarding.reminders.manage.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot create reminder." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Access token unavailable" description="Sign in again." />;
  }
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader
        eyebrow="F2.3"
        title="New safeguarding reminder"
        description="Schedule a privacy-conscious follow-up. Delivery uses the F2.2/F2.12 notification boundary."
      />
      <SafeguardingForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
      />
    </div>
  );
}
