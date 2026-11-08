import { redirect } from "next/navigation";
import { AiActivityPanel } from "@/components/ai/AiActivityPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canReadAiActivity } from "@/lib/aiActivityView";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function AiActivityPage() {
  const session = await requireAuthenticatedSession("/dashboard/ai-activity");
  const permissions = session.authorization?.permissions ?? [];
  if (!canReadAiActivity(permissions)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load AI activity." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          title="AI activity"
          description="Traceable AI operations with genuine source references and confidence signals. Wrong-answer feedback is reviewed by authorised staff — never used to auto-train models."
        />
        <AiActivityPanel
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          permissions={permissions}
        />
      </div>
    );
  } catch {
    return <ErrorState description="Unable to load AI activity." />;
  }
}
