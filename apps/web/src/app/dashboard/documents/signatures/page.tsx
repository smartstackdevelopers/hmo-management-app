import Link from "next/link";
import { redirect } from "next/navigation";
import { SignatureCompleteForm } from "@/components/documents/SignatureCompleteForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader, DataTable, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { getDocument, listMyPendingSignatures, listPendingSignatures } from "@/lib/managedDocumentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DocumentsSignaturesPage() {
  const session = await requireAuthenticatedSession("/dashboard/documents/signatures");
  const perms = session.authorization?.permissions;
  const canSeeOrg = canAny(perms, ["documents.read.meta"]);
  const canSign = canAny(perms, ["documents.sign.complete"]);
  if (!canSeeOrg && !canSign) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet." />;
  }
  const maybeToken = (await auth0.getAccessToken())?.token;
  if (!maybeToken) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  const token: string = maybeToken;
  const role = session.authorization?.active_role;
  const organisationId = orgId;

  try {
    const [orgPending, mine] = await Promise.all([
      canSeeOrg
        ? listPendingSignatures({ accessToken: token, organisationId: organisationId, role })
        : Promise.resolve([]),
      canSign
        ? listMyPendingSignatures({ accessToken: token, organisationId: organisationId, role })
        : Promise.resolve([]),
    ]);

    async function docTitle(documentId: string): Promise<string> {
      try {
        const d = await getDocument({
          accessToken: token,
          organisationId: organisationId,
          role: role ?? null,
          documentId,
        });
        return String((d as Record<string, string>).title ?? documentId);
      } catch {
        return documentId;
      }
    }

    const mineRaw = mine as Record<string, string>[];
    const mineRows: Array<Record<string, string> & { docTitle: string }> = await Promise.all(
      mineRaw.map(async (s) => ({
        ...s,
        docTitle: await docTitle(String(s.document_id)),
      })),
    );

    return (
      <div className="mx-auto max-w-3xl space-y-8">
        <PageHeader
          eyebrow="Documents"
          title="Signatures"
          description="Internal acknowledgement workflow — not a qualified trust-service signature. Provider integration is documented for future use."
        />
        {canSign && mineRows.length > 0 ? (
          <section className="space-y-4">
            <CardHeader title="Action required" description="You are the signer on these requests." />
            {mineRows.map((s) => (
              <Card key={s.id}>
                <p className="font-semibold text-slate-900">
                  <Link href={`/dashboard/documents/${s.document_id}`} className="hover:text-brand-700 hover:underline">
                    {s.docTitle}
                  </Link>
                </p>
                <p className="mt-1 text-xs text-slate-500">Version {s.version_id}</p>
                <div className="mt-4">
                  <SignatureCompleteForm
                    accessToken={token}
                    organisationId={organisationId}
                    role={role ?? null}
                    signatureId={String(s.id)}
                  />
                </div>
              </Card>
            ))}
          </section>
        ) : canSign ? (
          <EmptyState
            title="No signatures waiting on you"
            description="When someone requests your signature, it will appear here."
          />
        ) : null}

        {canSeeOrg ? (
          <section className="space-y-3">
            <CardHeader title="Organisation pending" />
            {(orgPending as Record<string, string>[]).length === 0 ? (
              <EmptyState title="None pending" description="No pending signature requests in the organisation queue." />
            ) : (
              <DataTable caption="Organisation pending signatures">
                <thead>
                  <tr>
                    <Th>Document</Th>
                    <Th>Signer</Th>
                    <Th>Status</Th>
                  </tr>
                </thead>
                <tbody>
                  {(orgPending as Record<string, string>[]).map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <Td>
                        <Link href={`/dashboard/documents/${s.document_id}`} className="font-semibold text-slate-900 hover:text-brand-700 hover:underline">
                          Open document
                        </Link>
                      </Td>
                      <Td>Assigned signer</Td>
                      <Td>
                        <StatusChip status={s.status} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </DataTable>
            )}
          </section>
        ) : null}
      </div>
    );
  } catch {
    return <ErrorState description={"Failed to load"} />;
  }
}
