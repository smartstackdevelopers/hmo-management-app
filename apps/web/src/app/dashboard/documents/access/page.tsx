import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { CardHeader, DataTable, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listMyAccessRequests, listPendingAccessRequests } from "@/lib/managedDocumentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DocumentsAccessPage() {
  const session = await requireAuthenticatedSession("/dashboard/documents/access");
  const perms = session.authorization?.permissions;
  const canRequest = canAny(perms, ["documents.access.request"]);
  const canReview = canAny(perms, ["documents.access.approve"]);
  if (!canRequest && !canReview) {
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
  const role = session.authorization?.active_role;

  try {
    const [mine, pending] = await Promise.all([
      canRequest
        ? listMyAccessRequests({ accessToken: token, organisationId: orgId, role })
        : Promise.resolve([]),
      canReview
        ? listPendingAccessRequests({ accessToken: token, organisationId: orgId, role })
        : Promise.resolve([]),
    ]);

    const mineRows = mine as Record<string, string>[];
    const pendingRows = pending as Record<string, string>[];

    const table = (rows: Record<string, string>[], caption: string) => (
      <DataTable caption={caption}>
        <thead>
          <tr>
            <Th>Document</Th>
            <Th>Status</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="hover:bg-slate-50">
              <Td>
                <Link href={`/dashboard/documents/${r.document_id}`} className="font-semibold text-slate-900 hover:text-brand-700 hover:underline">
                  Open document
                </Link>
              </Td>
              <Td>
                <StatusChip status={r.status} />
              </Td>
            </tr>
          ))}
        </tbody>
      </DataTable>
    );

    return (
      <div className="mx-auto max-w-3xl space-y-8">
        <PageHeader
          eyebrow="Documents"
          title="Access requests"
          description="Submitting a request does not grant access until an authorised reviewer approves."
        />
        {canRequest ? (
          <section className="space-y-3">
            <CardHeader title="My requests" />
            {mineRows.length === 0 ? (
              <EmptyState title="No requests" description="You have not submitted any document access requests." />
            ) : (
              table(mineRows, "My access requests")
            )}
          </section>
        ) : null}
        {canReview ? (
          <section className="space-y-3">
            <CardHeader title="Pending review" />
            {pendingRows.length === 0 ? (
              <EmptyState title="None pending" description="There are no requests awaiting your decision." />
            ) : (
              table(pendingRows, "Access requests pending review")
            )}
          </section>
        ) : null}
      </div>
    );
  } catch {
    return <ErrorState description={"Failed to load"} />;
  }
}
