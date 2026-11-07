import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { MaintenanceForm } from "@/components/maintenance/MaintenanceForm";
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
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot submit maintenance." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Session" description="Access token unavailable." />;
  }
  const role = session.authorization?.active_role;
  const perms = session.authorization?.permissions;
  const tenantMode = Boolean(perms?.includes("maintenance.create.own") && !perms?.includes("maintenance.create.assigned"));

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader eyebrow="Maintenance" title="Submit maintenance request" description="Operational repair request — not an emergency channel." />
      <MaintenanceForm accessToken={token} organisationId={orgId} role={role} tenantMode={tenantMode} />
    </div>
  );
}
