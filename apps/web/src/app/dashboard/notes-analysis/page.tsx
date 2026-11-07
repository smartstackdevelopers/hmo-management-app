import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
  if (!token) return <ErrorState description="Access token unavailable." />;

  let items: Array<Record<string, unknown>> = [];
  try {
    const res = await fetchNotesAnalysisInbox({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    items = res.items;
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load inbox"} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="F3.4"
        title="Notes analysis inbox"
        description="AI-generated note summaries and suggestions awaiting human review. AI content is never a verified staff statement."
      />
      {items.length === 0 ? (
        <EmptyState
          title="No pending analyses"
          description="Run analysis from an authorised daily note, or wait for the configured overnight batch."
        />
      ) : (
        <ul className="divide-y border-t border-slate-200">
          {items.map((item) => (
            <li key={String(item.source_id)} className="py-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-medium text-slate-900">{String(item.title)}</div>
                  <div className="text-sm text-slate-600">
                    {String(item.reference)} · {String(item.status)} · AI-generated
                  </div>
                </div>
                <Link className="text-sm text-blue-700 underline" href={`/dashboard/notes-analysis/${item.source_id}`}>
                  Review
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
