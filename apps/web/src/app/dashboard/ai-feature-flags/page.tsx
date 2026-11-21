import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canReadAiFeatureFlags } from "@/lib/aiFeatureFlagsView";
import { requireAuthenticatedSession } from "@/lib/session";
import { FlagsBoard } from "./FlagsBoard";

export default async function AiFeatureFlagsPage() {
  const session = await requireAuthenticatedSession("/dashboard/ai-feature-flags");
  const permissions = session.authorization?.permissions ?? [];
  if (!canReadAiFeatureFlags(permissions)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to manage AI features." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/ai-feature-flags" />;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="AI / Feature flags"
        title="AI feature flags"
        description="Turn AI features on or off per organisation. Every change is audited."
        actions={
          <Link href="#flag-history" className={btnPrimary}>
            View history
          </Link>
        }
      />
      <FlagsBoard
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
        permissions={permissions}
      />
    </div>
  );
}
