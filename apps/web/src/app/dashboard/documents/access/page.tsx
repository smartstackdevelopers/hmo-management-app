import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 to load access requests." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
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

    const row = (r: Record<string, string>) => (
      <li key={r.id} className="px-3 py-2 text-sm">
        <Link href={`/dashboard/documents/${r.document_id}`} className="font-medium text-teal-800 underline">
          Open document
        </Link>
        <span className="ml-2 text-slate-500">{r.status}</span>
      </li>
    );

    return (
      <div className="mx-auto max-w-3xl space-y-8">
        <PageHeader
          title="Access requests"
          description="Submitting a request does not grant access until an authorised reviewer approves."
        />
        {canRequest ? (
          <section>
            <h2 className="text-lg font-semibold">My requests</h2>
            {mineRows.length === 0 ? (
              <EmptyState title="No requests" description="You have not submitted any document access requests." />
            ) : (
              <ul className="mt-2 divide-y rounded-lg border bg-white">{mineRows.map(row)}</ul>
            )}
          </section>
        ) : null}
        {canReview ? (
          <section>
            <h2 className="text-lg font-semibold">Pending review</h2>
            {pendingRows.length === 0 ? (
              <EmptyState title="None pending" description="There are no requests awaiting your decision." />
            ) : (
              <ul className="mt-2 divide-y rounded-lg border bg-white">{pendingRows.map(row)}</ul>
            )}
          </section>
        ) : null}
      </div>
    );
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load"} />;
  }
}
