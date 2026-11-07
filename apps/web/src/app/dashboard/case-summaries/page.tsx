import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchCaseSummaryVersions } from "@/lib/caseSummariesApi";
import { canGenerateSummary, summaryLayoutClass } from "@/lib/caseSummaryView";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { GenerateSummaryButton } from "./GenerateSummaryButton";

export default async function CaseSummariesPage({
  searchParams,
}: {
  searchParams: Promise<{ tenantId?: string }>;
}) {
  const { tenantId } = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/case-summaries");
  const permissions = session.authorization?.permissions;
  if (
    session.authorization &&
    !canAny(permissions, ["ai.case_summary.run", "ai.case_summary.read", "ai.case_summary.review"])
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
  const allowGenerate = canGenerateSummary(permissions);

  let items: Array<Record<string, unknown>> = [];
  let loadError: string | null = null;
  if (tenantId) {
    try {
      const res = await fetchCaseSummaryVersions(tenantId, {
        accessToken: token,
        organisationId: orgId,
        role,
      });
      items = res.items;
    } catch (e) {
      loadError = e instanceof Error ? e.message : "Failed to load case summaries";
    }
  }

  return (
    <div className={summaryLayoutClass()}>
      <PageHeader
        eyebrow="F3.5"
        title="Case summaries"
        description="AI-generated summaries of authorised case records. Approval does not change support plans, case status, or housing decisions."
      />
      {!tenantId ? (
        <EmptyState
          title="Open a case first"
          description="Generate a summary from the case page. Summaries stay inside the active organisation and caseload."
        />
      ) : (
        <div className="space-y-4">
          {allowGenerate ? (
            <GenerateSummaryButton
              tenantId={tenantId}
              accessToken={token}
              organisationId={orgId}
              role={role}
            />
          ) : null}
          {loadError ? <ErrorState description={loadError} /> : null}
          {items.length === 0 && !loadError ? (
            <p className="text-sm text-slate-600">No summary versions yet for this case.</p>
          ) : (
            <ul className="divide-y border-t border-slate-200">
              {items.map((item) => (
                <li key={String(item.id)} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <div>
                    <div className="font-medium text-slate-900">Version {String(item.version_number)}</div>
                    <div className="text-sm text-slate-600">
                      {String(item.status)} · {String(item.generated_at ?? "")}
                      {item.stale ? " · may be outdated" : ""}
                    </div>
                  </div>
                  <Link className="text-sm text-teal-800 underline" href={`/dashboard/case-summaries/${item.id}`}>
                    View
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
