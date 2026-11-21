import { redirect } from "next/navigation";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { MaintenanceForm } from "@/components/maintenance/MaintenanceForm";
import { linkClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function MaintenanceNewPage() {
  const session = await requireAuthenticatedSession("/dashboard/maintenance/new");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "maintenance.manage",
      "maintenance.create.own",
      "maintenance.create.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select an organisation before reporting a repair." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in unavailable" description="We can't send repair reports right now. Please try again later." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Session expired" description="Please sign in again to report a repair." />;
  }
  const role = session.authorization?.active_role;
  const perms = session.authorization?.permissions;
  const tenantMode = Boolean(perms?.includes("maintenance.create.own") && !perms?.includes("maintenance.create.assigned"));

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link href="/dashboard/maintenance" className={`text-sm ${linkClass}`}>
        ← Back to repairs
      </Link>
      <PageHeader
        eyebrow="Maintenance"
        title="Report a repair"
        description="Tell us what needs fixing. For gas leaks, fire or anything dangerous, call the emergency services first."
      />
      <MaintenanceForm accessToken={token} organisationId={orgId} role={role} tenantMode={tenantMode} />
    </div>
  );
}
