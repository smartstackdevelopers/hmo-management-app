import Link from "next/link";
import { redirect } from "next/navigation";
import { ApplicationForm } from "@/components/housing/ApplicationForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { linkClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewHousingApplicationPage() {
  const session = await requireAuthenticatedSession("/dashboard/housing-applications/new");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "applications.manage",
      "applications.create.own",
      "applications.create.assigned",
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
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Sign in again" description="Sign in again." />;
  }
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link href="/dashboard/housing-applications" className={`text-sm ${linkClass}`}>
        ← Back to applications
      </Link>
      <PageHeader
        eyebrow="Housing"
        title="New housing application"
        description="Collect only the housing information needed for review."
      />
      <ApplicationForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
      />
    </div>
  );
}
