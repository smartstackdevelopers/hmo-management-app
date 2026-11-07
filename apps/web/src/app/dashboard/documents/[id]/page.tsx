import Link from "next/link";
import { redirect } from "next/navigation";
import { AccessRequestForm } from "@/components/documents/AccessRequestForm";
import { NewVersionUploadForm } from "@/components/documents/NewVersionUploadForm";
import { DocumentCheckPanel } from "@/components/documents/DocumentCheckPanel";
import { SecureDocumentDownload } from "@/components/documents/SecureDocumentDownload";
import { canRunDocumentCheck } from "@/lib/documentCheckView";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { getDocument, listDocumentVersions, listDocumentCategories } from "@/lib/managedDocumentsApi";
import { can, canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/documents/${id}`);
  if (session.authorization && !canAny(session.authorization.permissions, ["documents.read.meta"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 to load this page." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  const perms = session.authorization?.permissions;
  const role = session.authorization?.active_role;

  try {
    const [doc, versions, categories] = await Promise.all([
      getDocument({ accessToken: token, organisationId: orgId, role, documentId: id }),
      listDocumentVersions({ accessToken: token, organisationId: orgId, role, documentId: id }),
      listDocumentCategories({ accessToken: token, organisationId: orgId, role }).catch(() => []),
    ]);

    const d = doc as Record<string, string | boolean | null>;
    const catLabel = categories.find((c) => c.id === String(d.category_id))?.title ?? d.category_id;

    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <PageHeader
            eyebrow={String(d.reference_number ?? "")}
            title={String(d.title ?? "Document")}
            description={`Category: ${catLabel} · Status: ${String(d.status)} · Expiry: ${String(d.expiry_tracking)}`}
          />
          <Link href="/dashboard/documents/browse" className="text-sm text-teal-800 underline">
            Back to list
          </Link>
        </div>

        <dl className="grid gap-2 rounded-lg border border-slate-200 bg-white p-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Retention</dt>
            <dd className="font-medium">{String(d.retention_status)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Classification</dt>
            <dd className="font-medium">{String(d.effective_classification ?? d.access_classification)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Legal hold</dt>
            <dd className="font-medium">{d.legal_hold ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Expiry date</dt>
            <dd className="font-medium">{d.expiry_date ? String(d.expiry_date) : "—"}</dd>
          </div>
        </dl>

        <div className="flex flex-wrap gap-2">
          {can(perms, "documents.read.content") ? (
            <SecureDocumentDownload
              accessToken={token}
              organisationId={orgId}
              role={role}
              documentId={id}
            />
          ) : (
            <p className="text-sm text-slate-600">You do not have permission to download file content.</p>
          )}
        </div>

        <div>
          <h2 className="text-lg font-semibold text-forest-900">Versions</h2>
          {(versions as Record<string, unknown>[]).length === 0 ? (
            <p className="text-sm text-slate-600">No versions.</p>
          ) : (
            <ul className="mt-2 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white text-sm">
              {(versions as Record<string, string>[]).map((v) => (
                <li key={v.id} className="px-3 py-2">
                  v{v.version_number} · {v.change_description || "—"} · {v.created_at}
                </li>
              ))}
            </ul>
          )}
        </div>

        {canRunDocumentCheck(perms) ? (
          <DocumentCheckPanel
            documentId={id}
            accessToken={token}
            organisationId={orgId}
            role={role}
            permissions={perms ?? []}
          />
        ) : null}

        {can(perms, "documents.version") ? (
          <NewVersionUploadForm accessToken={token} organisationId={orgId} role={role} documentId={id} />
        ) : null}

        {can(perms, "documents.access.request") ? (
          <AccessRequestForm accessToken={token} organisationId={orgId} role={role} documentId={id} />
        ) : null}

        <p className="text-xs text-slate-500">
          Signature requests and approvals for this document are linked from the organisation signatures page when
          pending.
        </p>
      </div>
    );
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load document"} />;
  }
}
