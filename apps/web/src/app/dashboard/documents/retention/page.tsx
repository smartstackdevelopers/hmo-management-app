import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th } from "@/components/ui/primitives";
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
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;

  try {
    const page = await listRetentionPendingDocuments({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Documents"
          title="Retention review"
          description="Documents flagged for retention review. This app records metadata and reviews — it does not auto-delete."
        />
        {page.items.length === 0 ? (
          <EmptyState
            title="Nothing pending review"
            description="No documents have retention status pending review within your visibility rules."
          />
        ) : (
          <DataTable caption="Documents pending retention review">
            <thead>
              <tr>
                <Th>Document</Th>
                <Th>Reference</Th>
                <Th>Retention</Th>
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
                      <StatusChip status={r.retention_status} tone="amber" />
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
        )}
      </div>
    );
  } catch {
    return <ErrorState description={"Failed to load"} />;
  }
}
