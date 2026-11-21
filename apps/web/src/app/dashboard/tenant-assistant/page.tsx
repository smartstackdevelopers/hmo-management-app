import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { TenantAssistantPanel } from "@/components/tenant/TenantAssistantPanel";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAskTenantAssistant } from "@/lib/tenantAssistantView";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function TenantAssistantPage() {
  const session = await requireAuthenticatedSession("/dashboard/tenant-assistant");
  const permissions = session.authorization?.permissions ?? [];
  const role = session.authorization?.active_role;
  if (!canAskTenantAssistant(permissions, role)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow="AI"
          title="Tenant assistant"
          description="Pilot assistant that answers only from approved organisation content."
        />
        <TenantAssistantPanel accessToken={token} organisationId={orgId} role={role} />
      </div>
    );
  } catch {
    return <ErrorState description="Unable to load Tenant Assistant." />;
  }
}
