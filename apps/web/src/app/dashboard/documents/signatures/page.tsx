import Link from "next/link";
import { redirect } from "next/navigation";
import { SignatureCompleteForm } from "@/components/documents/SignatureCompleteForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 to load signatures." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
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
      <div className="mx-auto max-w-3xl space-y-10">
        <PageHeader
          title="Signatures"
          description="Internal acknowledgement workflow — not a qualified trust-service signature. Provider integration is documented for future use."
        />
        {canSign && mineRows.length > 0 ? (
          <section className="space-y-4">
            <h2 className="text-lg font-semibold">Action required (you are the signer)</h2>
            {mineRows.map((s) => (
              <div key={s.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="font-medium">
                  <Link href={`/dashboard/documents/${s.document_id}`} className="text-teal-800 underline">
                    {s.docTitle}
                  </Link>
                </p>
                <p className="text-xs text-slate-500">Version {s.version_id}</p>
                <div className="mt-3">
                  <SignatureCompleteForm
                    accessToken={token}
                    organisationId={organisationId}
                    role={role ?? null}
                    signatureId={String(s.id)}
                  />
                </div>
              </div>
            ))}
          </section>
        ) : canSign ? (
          <EmptyState
            title="No signatures waiting on you"
            description="When someone requests your signature, it will appear here."
          />
        ) : null}

        {canSeeOrg ? (
          <section>
            <h2 className="text-lg font-semibold">Organisation pending</h2>
            {(orgPending as Record<string, string>[]).length === 0 ? (
              <EmptyState title="None" description="No pending signature requests in the organisation queue." />
            ) : (
              <ul className="mt-2 divide-y rounded-lg border bg-white text-sm">
                {(orgPending as Record<string, string>[]).map((s) => (
                  <li key={s.id} className="px-3 py-2">
                    <Link href={`/dashboard/documents/${s.document_id}`} className="text-teal-800 underline">
                      Document
                    </Link>{" "}
                    · signer {String(s.signer_user_id ?? "").slice(0, 8)}… · {s.status}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : null}
      </div>
    );
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load"} />;
  }
}
