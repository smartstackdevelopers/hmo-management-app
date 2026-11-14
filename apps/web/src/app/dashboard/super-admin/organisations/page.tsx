import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { CreateOrganisationForm } from "@/components/platform/CreateOrganisationForm";
import { OrganisationsTable } from "@/components/platform/OrganisationsTable";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchPlatformOrganisations } from "@/lib/platformGovernanceApi";
import { requireDashboardRole } from "@/lib/session";

function parseGovernanceError(body: string): string {
  if (body.includes("Platform governance add-on disabled")) {
    return "Platform governance is disabled. Set PLATFORM_GOVERNANCE_GLOBAL_ENABLED=true on the API for local listing.";
  }
  if (body.includes("Forbidden") || body.includes("403")) {
    return "You do not have permission to list platform organisations.";
  }
  return body.slice(0, 400) || "Could not load organisations from the API.";
}

export default async function SuperAdminOrganisationsPage() {
  const session = await requireDashboardRole("super_admin", "/dashboard/super-admin/organisations");

  if (!isAuth0Configured() || !auth0) {
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <PageHeader
          eyebrow="Platform"
          title="Organisations"
          description="Configure Auth0 to load organisations from PostgreSQL."
        />
        <EmptyState title="Auth0 not configured" description="Sign-in is required for Super Admin organisation management." />
      </div>
    );
  }

  const token = (await auth0.getAccessToken())?.token;
  const orgId = session.authorization?.active_organisation_id;

  if (!token) {
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <PageHeader eyebrow="Platform" title="Organisations" description="Super Admin directory backed by FastAPI." />
        <ErrorState description="Access token unavailable. Sign in again." />
      </div>
    );
  }

  if (!orgId) {
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <PageHeader eyebrow="Platform" title="Organisations" description="Super Admin directory backed by FastAPI." />
        <EmptyState
          title="Organisation context required"
          description="Select an active organisation membership so API headers validate. Super Admin still uses platform-scoped endpoints."
        />
      </div>
    );
  }

  const auth = {
    accessToken: token,
    organisationId: orgId,
    role: session.authorization?.active_role ?? "super_admin",
  };

  let organisations: Awaited<ReturnType<typeof fetchPlatformOrganisations>> | null = null;
  let loadError: string | null = null;

  try {
    organisations = await fetchPlatformOrganisations(auth);
  } catch (err) {
    const body = err instanceof Error ? err.message : String(err);
    loadError = parseGovernanceError(body);
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader
        eyebrow="Platform"
        title="Organisations"
        description="Live directory from GET /api/v1/platform-governance/platform/organisations. Data is stored in PostgreSQL; nothing is invented in the browser."
      />
      {loadError ? <ErrorState title="Could not load organisations" description={loadError} /> : null}
      {!loadError && organisations && organisations.length === 0 ? (
        <EmptyState
          title="No organisations yet"
          description="Create the first organisation below or seed identity via the bootstrap CLI."
        />
      ) : null}
      {!loadError && organisations && organisations.length > 0 ? (
        <OrganisationsTable organisations={organisations} />
      ) : null}
      <CreateOrganisationForm auth={auth} />
    </div>
  );
}