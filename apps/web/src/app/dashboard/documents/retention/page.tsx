import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listRetentionPendingDocuments } from "@/lib/managedDocumentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DocumentsRetentionPage() {
  const session = await requireAuthenticatedSession("/dashboard/documents/retention");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["documents.read.meta", "documents.manage.retention"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 to load documents." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  try {
    const page = await listRetentionPendingDocuments({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <PageHeader
          title="Retention review"
          description="Documents flagged for retention review. This app records metadata and reviews — it does not auto-delete."
        />
        {page.items.length === 0 ? (
          <EmptyState
            title="Nothing pending review"
            description="No documents have retention_status pending_review within your visibility rules."
          />
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
                    {r.reference_number} · retention {r.retention_status}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    );
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load"} />;
  }
}
