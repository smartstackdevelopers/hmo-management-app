import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th, linkClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchNotesAnalysisInbox } from "@/lib/notesAnalysisApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NotesAnalysisInboxPage() {
  const session = await requireAuthenticatedSession("/dashboard/notes-analysis");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "ai.notes.analysis.inbox.read",
      "ai.notes.analysis.read",
      "ai.notes.analysis.review",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;

  let items: Array<Record<string, unknown>> = [];
  try {
    const res = await fetchNotesAnalysisInbox({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    items = res.items;
  } catch {
    return <ErrorState description={"Failed to load inbox"} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="AI"
        title="Notes analysis"
        description="AI-generated note summaries and suggestions awaiting human review. AI content is never a verified staff statement."
      />
      {items.length === 0 ? (
        <EmptyState
          title="No pending analyses"
          description="Run analysis from an authorised daily note, or wait for the configured overnight batch."
        />
      ) : (
        <DataTable caption="Notes analysis inbox">
          <thead>
            <tr>
              <Th>Note</Th>
              <Th>Reference</Th>
              <Th>Status</Th>
              <Th>Review</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={String(item.source_id)}>
                <Td className="font-semibold text-slate-900">{String(item.title)}</Td>
                <Td>{String(item.reference)}</Td>
                <Td>
                  <StatusChip status={String(item.status)} />
                </Td>
                <Td>
                  <Link className={linkClass} href={`/dashboard/notes-analysis/${item.source_id}`}>
                    Review
                  </Link>
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}
