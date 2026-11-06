import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { ShiftForm } from "@/components/ops/ShiftForm";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewShiftPage() {
  const session = await requireAuthenticatedSession("/dashboard/rota/new");
  if (session.authorization && !can(session.authorization.permissions, "organisation.users.manage")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot create shifts." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader eyebrow="Rota" title="New shift" description="Overlapping shifts for the same staff member are rejected." />
      <ShiftForm accessToken={token} organisationId={orgId} role={session.authorization?.active_role} />
    </div>
  );
}
