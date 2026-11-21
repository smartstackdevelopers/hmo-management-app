import { redirect } from "next/navigation";
import { OperationalSearchPanel } from "@/components/search/OperationalSearchPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canRunOperationalSearch } from "@/lib/operationalSearchView";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function OperationalSearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/operational-search");
  const permissions = session.authorization?.permissions ?? [];
  if (!canRunOperationalSearch(permissions)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to search." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so search can't load."
      />
    );
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) {
      return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/operational-search" />;
    }
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="Overview"
          title="Operational search"
          description="Ask a question about operational records you are already allowed to see. Results stay inside your organisation and role."
        />
        <OperationalSearchPanel
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          initialQuestion={q?.slice(0, 300)}
        />
      </div>
    );
  } catch {
    return <ErrorState description="Unable to load operational search." />;
  }
}
