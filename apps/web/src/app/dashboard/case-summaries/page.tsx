import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th, linkClass } from "@/components/ui/primitives";
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
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
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
    } catch {
      loadError = "We could not load this page. Please try again.";
    }
  }

  return (
    <div className={summaryLayoutClass()}>
      <PageHeader
        eyebrow="AI"
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
            <DataTable caption="Case summary versions">
              <thead>
                <tr>
                  <Th>Version</Th>
                  <Th>Status</Th>
                  <Th>Generated</Th>
                  <Th></Th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={String(item.id)}>
                    <Td className="font-semibold text-slate-900">Version {String(item.version_number)}</Td>
                    <Td>
                      <StatusChip status={String(item.status)} />
                      {item.stale ? <span className="ml-2 text-xs text-amber-700">May be outdated</span> : null}
                    </Td>
                    <Td className="whitespace-nowrap text-slate-500">{String(item.generated_at ?? "—")}</Td>
                    <Td>
                      <Link className={linkClass} href={`/dashboard/case-summaries/${item.id}`}>
                        View
                      </Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </div>
      )}
    </div>
  );
}
