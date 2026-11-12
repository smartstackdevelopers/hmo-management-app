import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny, type ApprovedRole } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { redirect } from "next/navigation";
import { LandlordEnterpriseClient } from "./LandlordEnterpriseClient";

/** Align with F6.1 nav: landlords own the tools; org/super admins may oversee via properties.* */
const LANDLORD_ENTERPRISE_ROLES: ApprovedRole[] = [
  "landlord",
  "organisation_admin",
  "super_admin",
];

export default async function LandlordDashboardPage() {
  // F6.1 enterprise surface (also landlord role home). Do not gate on landlord-only —
  // nav lists org_admin/super_admin and backend scopes landlords to owned properties.
  const session = await requireAuthenticatedSession("/dashboard/landlord");

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Auth0 not configured"
        description="Landlord enterprise tools require Auth0 environment variables."
      />
    );
  }

  if (!session.authorization) {
    return (
      <ErrorState description="Authorization snapshot unavailable. Confirm API connectivity and membership." />
    );
  }

  const activeRole = session.authorization.active_role as ApprovedRole | null;
  if (!activeRole || !LANDLORD_ENTERPRISE_ROLES.includes(activeRole)) {
    redirect("/unauthorized");
  }

  if (
    !canAny(session.authorization.permissions, [
      "properties.manage",
      "properties.read",
      "rent_records.manage",
      "inspections.manage",
      "repairs.status.read",
      "maintenance.read.property",
    ])
  ) {
    redirect("/unauthorized");
  }

  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load landlord enterprise tools." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <EmptyState title="Access token unavailable" description="Sign in again." />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        eyebrow="F6.1"
        title="Landlord enterprise"
        description="Portfolio analytics, rent records ledger, inspections and repair oversight for properties you own. All figures come from live HMore records."
      />
      <LandlordEnterpriseClient
        accessToken={token}
        organisationId={orgId}
        role={session.authorization.active_role}
      />
    </div>
  );
}
