import { redirect } from "next/navigation";
import { AiFeatureFlagsPanel } from "@/components/ai/AiFeatureFlagsPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canReadAiFeatureFlags } from "@/lib/aiFeatureFlagsView";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function AiFeatureFlagsPage() {
  const session = await requireAuthenticatedSession("/dashboard/ai-feature-flags");
  const permissions = session.authorization?.permissions ?? [];
  if (!canReadAiFeatureFlags(permissions)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load AI feature flags." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          title="AI feature flags"
          description="Enable or disable organisation AI capabilities for controlled pilots. Disabling blocks API and background execution; budgets and human approval still apply when enabled."
        />
        <AiFeatureFlagsPanel
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          permissions={permissions}
        />
      </div>
    );
  } catch {
    return <ErrorState description="Unable to load AI feature flags." />;
  }
}
