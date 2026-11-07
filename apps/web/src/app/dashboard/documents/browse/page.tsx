import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listDocuments } from "@/lib/managedDocumentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DocumentsBrowsePage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const params = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/documents/browse");
  if (session.authorization && !canAny(session.authorization.permissions, ["documents.read.meta"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 to load the document list." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  let page;
  try {
    page = await listDocuments({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      q: params.q,
      page: 1,
      pageSize: 50,
    });
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load"} />;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader title="Document library" description="Search by title or reference. Results respect your visibility rules." />
      <form method="get" className="flex flex-wrap gap-2">
        <input
          name="q"
          defaultValue={params.q ?? ""}
          placeholder="Search…"
          className="min-w-[240px] flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <button type="submit" className="rounded bg-teal-700 px-3 py-2 text-sm text-white">
          Search
        </button>
      </form>
      {page.items.length === 0 ? (
        <EmptyState title="No matches" description="Try a different search term." />
      ) : (
        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {page.items.map((row) => {
            const r = row as Record<string, string>;
            return (
              <li key={r.id} className="px-4 py-3">
                <Link href={`/dashboard/documents/${r.id}`} className="font-medium text-teal-800 underline">
                  {r.title}
                </Link>
                <p className="text-xs text-slate-500">
                  {r.reference_number} · status {r.status} · expiry {r.expiry_tracking}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
