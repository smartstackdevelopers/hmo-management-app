import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, FilterTabs, StatCard, StatGrid, StatusChip, Td, Th, humanize } from "@/components/ui/primitives";
import { fetchOrgAiDashboard, fetchPlatformAiDashboard } from "@/lib/aiCostApi";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { can, canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const ORG_PERMS = ["ai.cost.dashboard.view", "ai.usage.read"];
const PLATFORM_PERM = "ai.platform.cost.view";

function featureLabel(value: unknown): string {
  const raw = String(value ?? "").replace(/^ai\./, "").replace(/[._]+/g, " ").trim();
  if (!raw || raw === "unknown") return "—";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function BreakdownTable({
  title,
  rows,
  keyName,
}: {
  title: string;
  rows: Array<Record<string, unknown>>;
  keyName: string;
}) {
  if (!rows.length) {
    return (
      <section className="space-y-2">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        <p className="text-sm text-slate-500">No usage recorded for this breakdown.</p>
      </section>
    );
  }
  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      <DataTable caption={title}>
        <thead>
          <tr>
            <Th>{keyName === "feature_id" ? "Feature" : humanize(keyName)}</Th>
            <Th>Executions</Th>
            <Th>Actual cost</Th>
            <Th>Input tokens</Th>
            <Th>Output tokens</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${String(row[keyName])}-${index}`}>
              <Td className="font-semibold text-slate-900">
                {keyName === "feature_id" ? featureLabel(row[keyName]) : humanize(String(row[keyName] ?? ""))}
              </Td>
              <Td>{String(row.execution_count ?? 0)}</Td>
              <Td>{String(row.actual_cost ?? "Unavailable")}</Td>
              <Td>{String(row.input_tokens ?? 0)}</Td>
              <Td>{String(row.output_tokens ?? 0)}</Td>
            </tr>
          ))}
        </tbody>
      </DataTable>
      <p className="text-xs text-slate-500">
        Showing 1–{rows.length} of {rows.length}
      </p>
    </section>
  );
}

export default async function AiCostsPage({
  searchParams,
}: {
  searchParams?: Promise<{ period?: string; scope?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/ai-costs");
  const params = (await searchParams) ?? {};
  const perms = session.authorization?.permissions;
  const canOrg = canAny(perms, ORG_PERMS);
  const canPlatform = can(perms, PLATFORM_PERM);
  if (!canOrg && !canPlatform) {
    redirect("/unauthorized");
  }

  const orgId = session.authorization?.active_organisation_id;
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Authentication is not configured." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;

  const wantPlatform = params.scope === "platform" && canPlatform;
  const period = params.period;
  const query = period ? { period_key: period } : undefined;

  let data: Record<string, unknown>;
  try {
    if (wantPlatform) {
      data = await fetchPlatformAiDashboard({
        accessToken: token,
        organisationId: orgId ?? undefined,
        role: session.authorization?.active_role,
        query,
      });
    } else {
      if (!orgId) {
        return <EmptyState title="Unavailable" description="Organisation context required." />;
      }
      data = await fetchOrgAiDashboard({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization?.active_role,
        query,
      });
    }
  } catch {
    return <ErrorState description={"Failed to load AI costs"} />;
  }

  const budget = (data.budget as Record<string, unknown> | undefined) ?? {};
  const totals = (data.totals as Record<string, unknown> | undefined) ?? {};
  const exhausted = Boolean(budget.budget_exhausted);
  const approaching = Boolean(budget.approaching_limit);
  const empty = Boolean(data.empty);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="AI"
        title="AI costs"
        description="Organisation AI budget consumption and cost-per-feature from verified usage records."
      />

      {canPlatform ? (
        <FilterTabs
          tabs={[
            { label: "Organisation", href: "/dashboard/ai-costs", active: !wantPlatform },
            { label: "Platform", href: "/dashboard/ai-costs?scope=platform", active: wantPlatform },
          ]}
        />
      ) : null}

      <p className="text-sm text-slate-500">Figures use recorded usage only.</p>

      {exhausted ? (
        <div className="border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
          This organisation has reached its approved AI usage limit for the period. Further billable AI
          requests will be rejected.
        </div>
      ) : null}
      {approaching && !exhausted ? (
        <div className="border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="status">
          AI budget utilisation is approaching the configured warning threshold.
        </div>
      ) : null}

      {!wantPlatform ? (
        <StatGrid>
          <StatCard
            label="Monthly budget"
            value={
              budget.monthly_limit != null
                ? `${String(budget.currency ?? "")} ${String(budget.monthly_limit)}`.trim()
                : "Not configured"
            }
          />
          <StatCard label="Consumed" value={String(budget.consumed ?? "0")} />
          <StatCard label="Remaining" value={budget.remaining != null ? String(budget.remaining) : "—"} />
          <StatCard label="Utilisation" value={budget.utilisation_pct != null ? `${String(budget.utilisation_pct)}%` : "—"} />
        </StatGrid>
      ) : null}

      <StatGrid>
        <StatCard label="Executions" value={String(totals.execution_count ?? 0)} />
        <StatCard label="Actual cost" value={String(totals.actual_cost ?? "0")} />
        <StatCard label="Input tokens" value={String(totals.input_tokens ?? 0)} />
        <StatCard label="Output tokens" value={String(totals.output_tokens ?? 0)} />
        <StatCard label="Cache hits" value={String(totals.cache_hit_count ?? 0)} />
        <StatCard label="Premium escalations" value={String(totals.premium_escalation_count ?? 0)} />
        <StatCard label="Failed" value={String(totals.failed_count ?? 0)} tone="red" />
        <StatCard label="Rejected for budget" value={String(totals.rejected_budget_count ?? 0)} tone="amber" />
      </StatGrid>

      {empty ? (
        <EmptyState
          title="No AI usage yet"
          description="Usage appears after billable AI executions are metered through the shared AI service."
        />
      ) : null}

      <BreakdownTable
        title="Cost by feature"
        rows={(data.by_feature as Array<Record<string, unknown>>) ?? []}
        keyName="feature_id"
      />
      <BreakdownTable
        title="Cost by provider"
        rows={(data.by_provider as Array<Record<string, unknown>>) ?? []}
        keyName="provider"
      />
      <BreakdownTable
        title="Cost by model"
        rows={(data.by_model as Array<Record<string, unknown>>) ?? []}
        keyName="model_id"
      />

      {wantPlatform ? (
        <section className="space-y-3">
          <h2 className="text-base font-semibold text-slate-900">Organisations</h2>
          {((data.organisations as Array<Record<string, unknown>>) ?? []).length === 0 ? (
            <EmptyState title="No organisation usage" description="No organisation recorded usage in this period." />
          ) : (
            <DataTable caption="Organisation AI costs">
              <thead>
                <tr>
                  <Th>Organisation</Th>
                  <Th>Executions</Th>
                  <Th>Actual cost</Th>
                  <Th>Budget</Th>
                </tr>
              </thead>
              <tbody>
                {((data.organisations as Array<Record<string, unknown>>) ?? []).map((row, index) => {
                  const budgetRow = (row.budget as Record<string, unknown>) ?? {};
                  const status = budgetRow.budget_exhausted ? "rejected" : budgetRow.approaching_limit ? "pending" : "ok";
                  const statusLabel = budgetRow.budget_exhausted ? "Limit reached" : budgetRow.approaching_limit ? "Approaching limit" : "Within budget";
                  return (
                    <tr key={String(row.organisation_name ?? index)}>
                      <Td className="font-semibold text-slate-900">{String(row.organisation_name || "Organisation")}</Td>
                      <Td>{String(row.execution_count ?? 0)}</Td>
                      <Td>{String(row.actual_cost ?? "0")}</Td>
                      <Td>
                        <StatusChip status={status}>{statusLabel}</StatusChip>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </DataTable>
          )}
        </section>
      ) : null}

      <p className="text-xs text-slate-500">Generated at {String(data.generated_at ?? "")}</p>
    </div>
  );
}
