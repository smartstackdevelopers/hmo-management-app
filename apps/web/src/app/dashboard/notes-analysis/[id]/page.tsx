import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchNotesAnalysis } from "@/lib/notesAnalysisApi";
import { can, canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { AnalysisReviewActions, SuggestionActions } from "./ReviewActions";

export default async function NotesAnalysisDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/notes-analysis/${id}`);
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["ai.notes.analysis.read", "ai.notes.analysis.review"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const role = session.authorization?.active_role;
  const canReview = can(session.authorization?.permissions, "ai.notes.analysis.review");

  let data: Record<string, unknown>;
  try {
    data = await fetchNotesAnalysis(id, { accessToken: token, organisationId: orgId, role });
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load analysis"} />;
  }

  const source = (data.source_note as Record<string, unknown> | undefined) ?? {};
  const suggestions = (data.suggestions as Array<Record<string, unknown>>) ?? [];
  const stale = Boolean(data.stale);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="F3.4"
        title="Notes analysis review"
        description="Compare the original daily note with AI-generated assistance. Approvals do not automatically change case records."
      />
      <p className="text-sm text-slate-600">
        Status: {String(data.status)} · Method: {String(data.generation_method)} ·{" "}
        <span className="font-medium text-amber-800">AI-generated</span>
      </p>
      {stale ? (
        <div className="border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="status">
          Source note has changed since this analysis. Suggestions are stale — regenerate before applying decisions.
        </div>
      ) : null}

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Original daily note</h2>
        <p className="text-sm text-slate-600">Date: {String(source.log_date ?? "—")}</p>
        <p className="whitespace-pre-wrap border-l-2 border-slate-300 pl-3 text-sm">{String(source.summary ?? "")}</p>
        <p className="whitespace-pre-wrap text-sm text-slate-800">{String(source.notes ?? "")}</p>
        <Link className="text-sm text-blue-700 underline" href="/dashboard/daily-logs/new">
          Daily logs
        </Link>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">AI summary</h2>
        <p className="text-xs uppercase tracking-wide text-amber-800">AI-generated — not a verified staff statement</p>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{String(data.summary ?? "")}</p>
        {data.uncertainty_notes ? (
          <p className="text-sm text-slate-600">Uncertainty: {String(data.uncertainty_notes)}</p>
        ) : null}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Suggestions for human review</h2>
        {suggestions.length === 0 ? (
          <p className="text-sm text-slate-500">No discrete suggestions recorded.</p>
        ) : (
          suggestions.map((s) => (
            <div key={String(s.id)} className="border-b border-slate-200 py-3">
              <div className="text-xs uppercase text-slate-500">
                {String(s.kind)} · {String(s.review_status)}
                {s.is_interpretation ? " · interpretation" : " · explicit gap"}
              </div>
              <div className="font-medium">{String(s.title)}</div>
              <p className="text-sm text-slate-700">{String(s.body)}</p>
              {s.rationale ? <p className="text-xs text-slate-500">Why: {String(s.rationale)}</p> : null}
              {s.source_excerpt ? (
                <p className="text-xs text-slate-500">Source: {String(s.source_excerpt)}</p>
              ) : null}
              {s.review_status === "pending" && !stale ? (
                <SuggestionActions
                  analysisId={id}
                  suggestionId={String(s.id)}
                  canReview={canReview}
                  accessToken={token}
                  organisationId={orgId}
                  role={role}
                />
              ) : null}
            </div>
          ))
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Analysis decision</h2>
        <AnalysisReviewActions
          analysisId={id}
          canReview={canReview}
          accessToken={token}
          organisationId={orgId}
          role={role}
        />
      </section>
    </div>
  );
}
