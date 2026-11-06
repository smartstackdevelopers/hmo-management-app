import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { HandoverForm } from "@/components/support/HandoverForm";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewHandoverPage({
  searchParams,
}: {
  searchParams?: Promise<{ tenantId?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/handovers/new");
  const params = searchParams ? await searchParams : {};
  if (session.authorization && !can(session.authorization.permissions, "support_notes.create.assigned")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot create handovers." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        eyebrow="Support"
        title="New handover"
        description="Hand a case to another Support Worker in the same organisation."
      />
      <HandoverForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
        defaultTenantId={params.tenantId}
      />
    </div>
  );
}
