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
import { Card, CardHeader, DataTable, StatusChip, Td, Th, linkClass } from "@/components/ui/primitives";
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
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;

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
        <Link href="/dashboard/documents/browse" className={`text-sm ${linkClass}`}>
          ← Back to library
        </Link>
        <PageHeader
          eyebrow={String(d.reference_number ?? "")}
          title={String(d.title ?? "Document")}
          description={`Category: ${catLabel}`}
        />
        <div className="flex flex-wrap gap-2">
          <StatusChip status={String(d.status)} />
          <StatusChip status={String(d.expiry_tracking)} />
          {d.legal_hold ? <StatusChip tone="red">Legal hold</StatusChip> : null}
        </div>

        <Card>
          <CardHeader title="Record" />
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Retention</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{String(d.retention_status)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Classification</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{String(d.effective_classification ?? d.access_classification)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Legal hold</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{d.legal_hold ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Expiry date</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{d.expiry_date ? String(d.expiry_date) : "—"}</dd>
            </div>
          </dl>
        </Card>

        <div className="flex flex-wrap gap-2">
          {can(perms, "documents.read.content") ? (
            <SecureDocumentDownload
              accessToken={token}
              organisationId={orgId}
              role={role}
              documentId={id}
            />
          ) : (
            <p className="text-sm text-slate-600">Downloading the file isn't available on your account.</p>
          )}
        </div>

        <div className="space-y-3">
          <CardHeader title="Versions" />
          {(versions as Record<string, unknown>[]).length === 0 ? (
            <EmptyState title="No versions" description="This document has no file versions yet." />
          ) : (
            <DataTable caption="Document versions">
              <thead>
                <tr>
                  <Th>Version</Th>
                  <Th>Change</Th>
                  <Th>Created</Th>
                </tr>
              </thead>
              <tbody>
                {(versions as Record<string, string>[]).map((v) => (
                  <tr key={v.id}>
                    <Td className="font-semibold text-slate-900">v{v.version_number}</Td>
                    <Td>{v.change_description || "—"}</Td>
                    <Td className="whitespace-nowrap text-slate-500">{v.created_at}</Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
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
  } catch {
    return <ErrorState description={"Failed to load document"} />;
  }
}
