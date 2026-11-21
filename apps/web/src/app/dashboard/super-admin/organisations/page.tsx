import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { CreateOrganisationForm } from "@/components/platform/CreateOrganisationForm";
import {
  Avatar,
  DataTable,
  FilterTabs,
  StatusChip,
  Td,
  Th,
  btnPrimary,
  btnSecondary,
  humanize,
  inputClass,
} from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchPlatformOrganisations, type PlatformOrganisation } from "@/lib/platformGovernanceApi";
import { requireDashboardRole } from "@/lib/session";

function hrefFor(status: string, q?: string) {
  const search = new URLSearchParams();
  if (status && status !== "all") search.set("status", status);
  if (q) search.set("q", q);
  const query = search.toString();
  return query ? `/dashboard/super-admin/organisations?${query}` : "/dashboard/super-admin/organisations";
}

export default async function SuperAdminOrganisationsPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string; status?: string }>;
}) {
  const session = await requireDashboardRole("super_admin", "/dashboard/super-admin/organisations");
  const params = searchParams ? await searchParams : {};
  const query = (params.q ?? "").trim();
  const header = (
    <PageHeader
      eyebrow="Platform / Organisations"
      title="Organisations"
      description="Create, configure and monitor tenant organisations."
      actions={
        <a href="#create-organisation" className={btnPrimary}>
          + New organisation
        </a>
      }
    />
  );

  if (!isAuth0Configured() || !auth0) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        {header}
        <EmptyState
          title="Sign-in not configured"
          description="Sign-in isn't set up in this environment yet, so organisations can't load."
        />
      </div>
    );
  }

  const token = (await auth0.getAccessToken())?.token;
  const orgId = session.authorization?.active_organisation_id;

  if (!token) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        {header}
        <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/super-admin/organisations" />
      </div>
    );
  }

  if (!orgId) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        {header}
        <EmptyState
          title="Choose an organisation"
          description="Select the organisation you're working in. Platform organisation tools stay available to Super Admin."
        />
      </div>
    );
  }

  const auth = {
    accessToken: token,
    organisationId: orgId,
    role: session.authorization?.active_role ?? "super_admin",
  };

  let organisations: PlatformOrganisation[] | null = null;
  try {
    organisations = await fetchPlatformOrganisations(auth);
  } catch {
    organisations = null;
  }

  const statuses = Array.from(new Set((organisations ?? []).map((org) => org.status).filter(Boolean)));
  const status = params.status && (params.status === "all" || statuses.includes(params.status)) ? params.status : "all";
  const visible = (organisations ?? []).filter((org) => {
    const haystack = `${org.name} ${org.slug}`.toLowerCase();
    const matchesQuery = !query || haystack.includes(query.toLowerCase());
    return matchesQuery && (status === "all" || org.status === status);
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {header}
      {organisations === null ? (
        <ErrorState
          title="Couldn't load organisations"
          description="We couldn't load organisations. Please try again."
          retryHref="/dashboard/super-admin/organisations"
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
              {status !== "all" ? <input type="hidden" name="status" value={status} /> : null}
              <label className="sr-only" htmlFor="organisation-search">
                Search organisations
              </label>
              <input id="organisation-search" name="q" defaultValue={query} placeholder="Search organisations" className={inputClass} />
              <button type="submit" className={btnSecondary}>
                Search
              </button>
            </form>
            <FilterTabs
              tabs={[
                { label: "All", href: hrefFor("all", query || undefined), active: status === "all", count: organisations.length },
                ...statuses.map((value) => ({
                  label: humanize(value),
                  href: hrefFor(value, query || undefined),
                  active: status === value,
                  count: organisations.filter((org) => org.status === value).length,
                })),
              ]}
            />
          </div>
          {visible.length === 0 ? (
            <EmptyState
              title={organisations.length === 0 ? "No organisations yet" : "No matching organisations"}
              description={
                organisations.length === 0
                  ? "Create the first organisation with the form on this page."
                  : "Nothing matches this search."
              }
              action={query || status !== "all" ? { label: "Clear filters", href: "/dashboard/super-admin/organisations" } : undefined}
            />
          ) : (
            <DataTable caption="Organisations">
              <thead>
                <tr>
                  <Th>Organisation</Th>
                  <Th>Slug</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {visible.map((org) => (
                  <tr key={org.id} className="hover:bg-slate-50">
                    <Td>
                      <span className="flex items-center gap-3">
                        <Avatar name={org.name} size="sm" />
                        <span className="font-semibold text-slate-900">{org.name}</span>
                      </span>
                    </Td>
                    <Td>{org.slug}</Td>
                    <Td>
                      <StatusChip status={org.status} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
          <p className="text-xs text-slate-500">
            Showing {visible.length === 0 ? "0" : `1–${visible.length}`} of {organisations.length}
          </p>
        </>
      )}
      <CreateOrganisationForm auth={auth} />
    </div>
  );
}
