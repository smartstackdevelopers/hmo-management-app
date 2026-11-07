import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchCaseSummary } from "@/lib/caseSummariesApi";
import { canGenerateSummary, canReviewSummary, isSummaryStale, sectionEntries, summaryLayoutClass } from "@/lib/caseSummaryView";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { GenerateSummaryButton } from "../GenerateSummaryButton";
import { SummaryReviewActions } from "./ReviewActions";

export default async function CaseSummaryDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/case-summaries/${id}`);
  const permissions = session.authorization?.permissions;
  if (session.authorization && !canAny(permissions, ["ai.case_summary.read", "ai.case_summary.review"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const role = session.authorization?.active_role;

  let data: Record<string, unknown>;
  try {
    data = await fetchCaseSummary(id, { accessToken: token, organisationId: orgId, role });
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load case summary"} />;
  }

  const sections = sectionEntries(data.sections as Record<string, unknown> | undefined);
  const missing = (data.missing_information as string[] | undefined) ?? [];
  const concerns = (data.recorded_concerns as Array<Record<string, unknown>> | undefined) ?? [];
  const sources = (data.source_refs as Array<Record<string, unknown>> | undefined) ?? [];
  const stale = isSummaryStale(data);
  const pending = data.status === "pending_review";

  return (
    <div className={summaryLayoutClass()}>
      <PageHeader
        eyebrow="F3.5"
        title={`Case summary v${String(data.version_number)}`}
        description="AI-generated assistance for human review. Approving this summary does not edit case records."
      />
      <p className="text-sm text-slate-600">
        Status: {String(data.status)} · Generated: {String(data.generated_at ?? "—")} · Method:{" "}
        {String(data.generation_method)} · <span className="font-medium text-amber-800">AI-generated</span>
      </p>
      {data.covered_from || data.covered_to ? (
        <p className="text-sm text-slate-600">
          Records covered: {String(data.covered_from ?? "—")} to {String(data.covered_to ?? "—")}
        </p>
      ) : null}
      {stale ? (
        <div className="border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="status">
          Source records have changed since this version. The summary may be outdated.
        </div>
      ) : null}
      {canGenerateSummary(permissions) ? (
        <GenerateSummaryButton
          tenantId={String(data.tenant_id)}
          accessToken={token}
          organisationId={orgId}
          role={role}
          force
          label="Generate updated version"
        />
      ) : null}

      {sections.map((section) => (
        <section key={section.key} className="space-y-2">
          <h2 className="text-lg font-medium">{section.label}</h2>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{section.body}</p>
        </section>
      ))}

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Missing or unclear information</h2>
        {missing.length === 0 ? (
          <p className="text-sm text-slate-600">No missing-information items were recorded.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-800">
            {missing.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Recorded concerns</h2>
        <p className="text-xs text-slate-500">Only concerns explicitly present on source records are listed.</p>
        {concerns.length === 0 ? (
          <p className="text-sm text-slate-600">No explicit concerns were found in the source records.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {concerns.map((item) => (
              <li key={String(item.source_id)} className="border-l-2 border-slate-300 pl-3">
                {String(item.text)}{" "}
                <span className="text-xs text-slate-500">
                  ({String(item.source_type)} {String(item.source_id)})
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Source references</h2>
        {sources.length === 0 ? (
          <p className="text-sm text-slate-600">No source identifiers were stored.</p>
        ) : (
          <ul className="space-y-1 text-sm text-slate-700">
            {sources.map((item) => (
              <li key={`${item.type}-${item.id}`}>
                {String(item.type)} · {String(item.id)}
                {item.updated_at ? ` · updated ${String(item.updated_at)}` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>

      {data.uncertainty_notes ? (
        <p className="text-sm text-slate-600">Uncertainty: {String(data.uncertainty_notes)}</p>
      ) : null}

      {pending ? (
        <SummaryReviewActions
          summaryId={id}
          canReview={canReviewSummary(permissions)}
          accessToken={token}
          organisationId={orgId}
          role={role}
        />
      ) : (
        <p className="text-sm text-slate-600">
          Reviewed by {String(data.reviewed_by_user_id ?? "—")} at {String(data.reviewed_at ?? "—")}
          {data.review_comment ? ` · ${String(data.review_comment)}` : ""}
        </p>
      )}

      <Link className="text-sm text-teal-800 underline" href={`/dashboard/caseload/${String(data.tenant_id)}`}>
        Back to case
      </Link>
    </div>
  );
}
