import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th, btnPrimary, inputClass } from "@/components/ui/primitives";
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
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;

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
  } catch {
    return <ErrorState description={"Failed to load"} />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Compliance / Documents"
        title="Document library"
        description="Search by title or reference. Results respect your visibility rules."
      />
      <form method="get" className="flex flex-wrap items-center gap-2">
        <label htmlFor="document-search" className="sr-only">
          Search documents
        </label>
        <input
          id="document-search"
          name="q"
          defaultValue={params.q ?? ""}
          placeholder="Search title or reference"
          className={`min-w-[240px] max-w-md flex-1 ${inputClass}`}
        />
        <button type="submit" className={btnPrimary}>
          Search
        </button>
      </form>
      {page.items.length === 0 ? (
        <EmptyState
          title="No matches"
          description={params.q ? "Try a different search term." : "No documents are visible to you yet."}
          action={params.q ? { label: "Clear search", href: "/dashboard/documents/browse" } : undefined}
        />
      ) : (
        <DataTable caption="Documents">
          <thead>
            <tr>
              <Th>Document</Th>
              <Th>Reference</Th>
              <Th>Status</Th>
              <Th>Expiry</Th>
            </tr>
          </thead>
          <tbody>
            {page.items.map((row) => {
              const r = row as Record<string, string>;
              return (
                <tr key={r.id} className="hover:bg-slate-50">
                  <Td>
                    <Link href={`/dashboard/documents/${r.id}`} className="font-semibold text-slate-900 hover:text-brand-700 hover:underline">
                      {r.title}
                    </Link>
                  </Td>
                  <Td className="text-slate-500">{r.reference_number}</Td>
                  <Td>
                    <StatusChip status={r.status} />
                  </Td>
                  <Td>
                    <StatusChip status={r.expiry_tracking} />
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}
