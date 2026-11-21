import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canReadAiActivity } from "@/lib/aiActivityView";
import { requireAuthenticatedSession } from "@/lib/session";
import { ActivityBoard } from "./ActivityBoard";

export default async function AiActivityPage() {
  const session = await requireAuthenticatedSession("/dashboard/ai-activity");
  const permissions = session.authorization?.permissions ?? [];
  if (!canReadAiActivity(permissions)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see AI activity." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/ai-activity" />;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="AI / Activity"
        title="AI activity"
        description="Every AI suggestion, who reviewed it and the outcome."
      />
      <ActivityBoard
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
        permissions={permissions}
      />
    </div>
  );
}
