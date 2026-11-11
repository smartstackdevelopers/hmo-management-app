import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listAdminCommunityServices } from "@/lib/communityDirectoryApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function statusClass(status: string): string {
  if (status === "verified") return "text-teal-800";
  if (status === "outdated") return "text-amber-700";
  if (status === "inactive") return "text-red-700";
  if (status === "needs_review") return "text-orange-700";
  return "text-slate-700";
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
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load community directory." />;
  }
  const params = searchParams ? await searchParams : {};
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
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
    const totalPages = Math.max(1, Math.ceil(result.total / result.page_size));
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F5.1"
          title="Community directory"
          description="Manage food banks, community kitchens and clothing banks. New listings start as pending verification — never auto-verified."
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link
            href="/dashboard/community-directory/new"
            className="rounded-md bg-teal-700 px-3 py-2 text-white"
          >
            New listing
          </Link>
          <Link href="/dashboard/community-directory" className="rounded-md border border-slate-300 px-3 py-2">
            All
          </Link>
          <Link
            href="/dashboard/community-directory?verification_status=pending_verification"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Pending verification
          </Link>
          <Link
            href="/dashboard/community-directory?verification_status=needs_review"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Needs review
          </Link>
          <Link
            href="/dashboard/community-directory?category=food_bank"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Food banks
          </Link>
          <Link
            href="/dashboard/community-directory?category=kitchen"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Kitchens
          </Link>
          <Link
            href="/dashboard/community-directory?category=clothing_bank"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Clothing banks
          </Link>
        </div>
        <form className="flex flex-wrap gap-2" method="get">
          <input
            name="q"
            defaultValue={params.q ?? ""}
            placeholder="Search by name"
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          />
          {params.category ? <input type="hidden" name="category" value={params.category} /> : null}
          {params.verification_status ? (
            <input type="hidden" name="verification_status" value={params.verification_status} />
          ) : null}
          <button type="submit" className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            Search
          </button>
          <Link href="/dashboard/community-directory" className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            Reset
          </Link>
        </form>
        {result.items.length === 0 ? (
          <EmptyState
            title="No directory listings"
            description="Create a service listing, then verify it before tenants rely on the details."
          />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {result.items.map((row) => (
              <li key={row.id} className="p-4 text-sm">
                <Link
                  href={`/dashboard/community-directory/${row.id}`}
                  className="font-medium text-forest-900 hover:underline"
                >
                  {row.name}
                </Link>
                <p className={statusClass(row.verification_status)}>
                  {row.category.replaceAll("_", " ")} · {row.verification_status.replaceAll("_", " ")}
                  {row.is_published ? " · published" : " · draft"}
                </p>
                <p className="text-slate-600">
                  {row.address_line || "Address not provided"} · Hours:{" "}
                  {row.opening_hours || "not provided"}
                </p>
              </li>
            ))}
          </ul>
        )}
        {totalPages > 1 ? (
          <div className="flex items-center gap-3 text-sm">
            {page > 1 ? (
              <Link
                href={`/dashboard/community-directory?page=${page - 1}${params.q ? `&q=${encodeURIComponent(params.q)}` : ""}${params.category ? `&category=${params.category}` : ""}${params.verification_status ? `&verification_status=${params.verification_status}` : ""}`}
                className="rounded-md border border-slate-300 px-3 py-2"
              >
                Previous
              </Link>
            ) : null}
            <span>
              Page {page} of {totalPages}
            </span>
            {page < totalPages ? (
              <Link
                href={`/dashboard/community-directory?page=${page + 1}${params.q ? `&q=${encodeURIComponent(params.q)}` : ""}${params.category ? `&category=${params.category}` : ""}${params.verification_status ? `&verification_status=${params.verification_status}` : ""}`}
                className="rounded-md border border-slate-300 px-3 py-2"
              >
                Next
              </Link>
            ) : null}
          </div>
        ) : null}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load community directory."}
      />
    );
  }
}
