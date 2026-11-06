import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DailyLogForm } from "@/components/support/DailyLogForm";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewDailyLogPage({
  searchParams,
}: {
  searchParams?: Promise<{ tenantId?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/daily-logs/new");
  const params = searchParams ? await searchParams : {};
  if (session.authorization && !can(session.authorization.permissions, "support_notes.create.assigned")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot create daily logs." />;
  }
  const tokenResult = await auth0.getAccessToken();
  const token = tokenResult?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        eyebrow="Support"
        title="New daily log"
        description="Record support activity for an assigned tenant. Note bodies are not written to application audit metadata."
      />
      <DailyLogForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
        defaultTenantId={params.tenantId}
      />
    </div>
  );
}
