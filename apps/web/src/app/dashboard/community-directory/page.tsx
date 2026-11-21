import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Avatar, btnPrimary, btnSecondary, DataTable, FilterTabs, inputClass, linkClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listAdminCommunityServices } from "@/lib/communityDirectoryApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function listingStatus(status: string, published: boolean): string {
  if (published && status === "verified") return "published";
  return status;
}

function queryHref(params: { q?: string; category?: string; verification_status?: string; page?: number }) {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.category) search.set("category", params.category);
  if (params.verification_status) search.set("verification_status", params.verification_status);
  if (params.page && params.page > 1) search.set("page", String(params.page));
  const query = search.toString();
  return query ? `/dashboard/community-directory?${query}` : "/dashboard/community-directory";
}

export default async function CommunityDirectoryPage({
  searchParams,
}: {
  searchParams?: Promise<{
    q?: string;
    category?: string;
    verification_status?: string;
    page?: string;
  }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/community-directory");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "organisations.manage",
      "organisation.settings.manage",
    ]) &&
    session.authorization.active_role !== "organisation_admin" &&
    session.authorization.active_role !== "super_admin"
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to manage the directory." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="The community directory will be available once sign-in is configured." />;
  }
  const params = searchParams ? await searchParams : {};
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/community-directory" />;
    const result = await listAdminCommunityServices({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      q: params.q,
      category: params.category,
      verification_status: params.verification_status,
      page,
      page_size: 25,
    });
    const from = result.total === 0 ? 0 : (page - 1) * result.page_size + 1;
    const to = Math.min(page * result.page_size, result.total);
    const filtered = Boolean(params.q || params.category || params.verification_status);
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Community / Directory"
          title="Community directory"
          description="Verified local services shown to tenants."
          actions={
            <Link href="/dashboard/community-directory/new" className={btnPrimary}>
              + Add service
            </Link>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {params.category ? <input type="hidden" name="category" value={params.category} /> : null}
            {params.verification_status ? <input type="hidden" name="verification_status" value={params.verification_status} /> : null}
            <label className="sr-only" htmlFor="directory-search">
              Search services
            </label>
            <input id="directory-search" name="q" defaultValue={params.q ?? ""} placeholder="Search services" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: queryHref({ q: params.q }), active: !params.verification_status && !params.category },
              { label: "Published", href: queryHref({ q: params.q, verification_status: "verified" }), active: params.verification_status === "verified" },
              { label: "Pending", href: queryHref({ q: params.q, verification_status: "pending_verification" }), active: params.verification_status === "pending_verification" },
              { label: "Needs review", href: queryHref({ q: params.q, verification_status: "needs_review" }), active: params.verification_status === "needs_review" },
              { label: "Food banks", href: queryHref({ q: params.q, category: "food_bank" }), active: params.category === "food_bank" },
              { label: "Kitchens", href: queryHref({ q: params.q, category: "kitchen" }), active: params.category === "kitchen" },
              { label: "Clothing", href: queryHref({ q: params.q, category: "clothing_bank" }), active: params.category === "clothing_bank" },
            ]}
          />
        </div>
        {result.items.length === 0 ? (
          <EmptyState
            title="No directory listings"
            description={filtered ? "No services match these filters." : "Add a service, then verify it before tenants rely on it."}
            action={filtered ? { label: "Clear filters", href: "/dashboard/community-directory" } : { label: "Add service", href: "/dashboard/community-directory/new" }}
          />
        ) : (
          <DataTable caption="Community services">
            <thead>
              <tr>
                <Th>Service</Th>
                <Th>Category</Th>
                <Th>Updated</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {result.items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/60">
                  <Td>
                    <div className="flex items-center gap-3">
                      <Avatar name={row.name} size="sm" />
                      <div>
                        <Link href={`/dashboard/community-directory/${row.id}`} className={linkClass}>
                          {row.name}
                        </Link>
                        <p className="mt-0.5 text-xs text-slate-500">{row.address_line || "Address not provided"}</p>
                      </div>
                    </div>
                  </Td>
                  <Td>{row.category.replaceAll("_", " ")}</Td>
                  <Td>{row.updated_at ? new Date(row.updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "—"}</Td>
                  <Td>
                    <StatusChip status={listingStatus(row.verification_status, row.is_published)} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
          <p>
            Showing {from}–{to} of {result.total}
          </p>
          <div className="flex gap-2">
            {page > 1 ? (
              <Link className={btnSecondary} href={queryHref({ q: params.q, category: params.category, verification_status: params.verification_status, page: page - 1 })}>
                Previous
              </Link>
            ) : null}
            {to < result.total ? (
              <Link className={btnSecondary} href={queryHref({ q: params.q, category: params.category, verification_status: params.verification_status, page: page + 1 })}>
                Next
              </Link>
            ) : null}
          </div>
        </div>
      </div>
    );
  } catch {
    return (
      <ErrorState
        description="We couldn't load the community directory. Please try again."
        retryHref="/dashboard/community-directory"
      />
    );
  }
}
