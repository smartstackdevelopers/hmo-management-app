import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchDocumentsDashboard, listDocuments } from "@/lib/managedDocumentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DocumentsDashboardPage() {
  const session = await requireAuthenticatedSession("/dashboard/documents");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["documents.read.meta"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load documents." />;
  }

  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }

  const role = session.authorization?.active_role;
  let dashboard: Record<string, unknown> | null = null;
  let recentList: unknown[] = [];
  let loadError: string | null = null;
  try {
    const dash = await fetchDocumentsDashboard({ accessToken: token, organisationId: orgId, role });
    dashboard = dash;
    const fromDash = dash.recently_updated;
    if (Array.isArray(fromDash) && fromDash.length > 0) {
      recentList = fromDash;
    } else {
      const list = await listDocuments({ accessToken: token, organisationId: orgId, role, page: 1, pageSize: 8 });
      recentList = list.items;
    }
  } catch (e) {
    loadError = e instanceof Error ? e.message : "Unable to load documents";
  }

  if (loadError) {
    return <ErrorState description={loadError} />;
  }

  const num = (k: string) => (typeof dashboard?.[k] === "number" ? (dashboard[k] as number) : "—");
  const byCat = dashboard?.by_category;
  const catRows =
    byCat && typeof byCat === "object" && byCat !== null
      ? Object.entries(byCat as Record<string, number>)
      : [];

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <PageHeader
        eyebrow="F2.11"
        title="Document management"
        description="Dashboard figures come from /api/v1/documents/dashboard. Downloads use authenticated API routes only."
      />

      <div className="flex flex-wrap gap-2 text-sm">
        <Link className="rounded border border-slate-300 px-3 py-2" href="/dashboard/documents/browse">
          All documents
        </Link>
        <Link className="rounded border border-slate-300 px-3 py-2" href="/dashboard/documents/new">
          Upload
        </Link>
        <Link className="rounded border border-slate-300 px-3 py-2" href="/dashboard/documents/expiring">
          Expiring soon
        </Link>
        <Link className="rounded border border-slate-300 px-3 py-2" href="/dashboard/documents/expired">
          Expired
        </Link>
        <Link className="rounded border border-slate-300 px-3 py-2" href="/dashboard/documents/retention">
          Retention review
        </Link>
        <Link className="rounded border border-slate-300 px-3 py-2" href="/dashboard/documents/access">
          Access requests
        </Link>
        <Link className="rounded border border-slate-300 px-3 py-2" href="/dashboard/documents/signatures">
          Signatures
        </Link>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {(
          [
            ["Total (visible)", "total_documents"],
            ["Expiring soon", "expiring_soon"],
            ["Expired", "expired"],
            ["Retention review", "pending_retention_review"],
            ["Pending access", "pending_access_requests"],
            ["Pending signatures", "pending_signatures"],
          ] as const
        ).map(([label, key]) => (
          <div key={key} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-forest-900">{num(key)}</p>
          </div>
        ))}
      </div>

      {catRows.length > 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm font-medium text-slate-700">Documents by category</p>
          <ul className="mt-2 divide-y divide-slate-100 text-sm">
            {catRows.map(([code, count]) => (
              <li key={code} className="flex justify-between py-2">
                <span className="text-slate-600">{code}</span>
                <span className="font-medium text-forest-900">{count}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div>
        <h2 className="text-lg font-semibold text-forest-900">Recently updated</h2>
        {recentList.length === 0 ? (
          <EmptyState title="No documents" description="Upload a document to see it listed here." />
        ) : (
          <ul className="mt-2 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {(recentList as Record<string, string>[]).map((row) => (
              <li key={row.id} className="px-4 py-3">
                <Link href={`/dashboard/documents/${row.id}`} className="font-medium text-teal-800 underline">
                  {row.title}
                </Link>
                <p className="text-xs text-slate-500">
                  {row.reference_number} · {row.expiry_tracking}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
