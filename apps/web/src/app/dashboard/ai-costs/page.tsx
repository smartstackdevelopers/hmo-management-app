import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { fetchOrgAiDashboard, fetchPlatformAiDashboard } from "@/lib/aiCostApi";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { can, canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const ORG_PERMS = ["ai.cost.dashboard.view", "ai.usage.read"];
const PLATFORM_PERM = "ai.platform.cost.view";

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border-b border-slate-200 py-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-900">{value}</div>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
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
        <h2 className="text-lg font-medium text-slate-900">{title}</h2>
        <p className="text-sm text-slate-500">No usage recorded for this breakdown.</p>
      </section>
    );
  }
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-medium text-slate-900">{title}</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-slate-500">
            <tr>
              <th className="py-2 pr-4 font-medium">{keyName}</th>
              <th className="py-2 pr-4 font-medium">Executions</th>
              <th className="py-2 pr-4 font-medium">Actual cost</th>
              <th className="py-2 pr-4 font-medium">Input tokens</th>
              <th className="py-2 font-medium">Output tokens</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row[keyName])} className="border-b border-slate-100">
                <td className="py-2 pr-4">{String(row[keyName] ?? "unknown")}</td>
                <td className="py-2 pr-4">{String(row.execution_count ?? 0)}</td>
                <td className="py-2 pr-4">{String(row.actual_cost ?? "unavailable")}</td>
                <td className="py-2 pr-4">{String(row.input_tokens ?? 0)}</td>
                <td className="py-2">{String(row.output_tokens ?? 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
  if (!token) return <ErrorState description="Access token unavailable." />;

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
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load AI costs"} />;
  }

  const budget = (data.budget as Record<string, unknown> | undefined) ?? {};
  const totals = (data.totals as Record<string, unknown> | undefined) ?? {};
  const exhausted = Boolean(budget.budget_exhausted);
  const approaching = Boolean(budget.approaching_limit);
  const empty = Boolean(data.empty);

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="F3.3"
        title="AI cost dashboard"
        description="Organisation AI budget consumption and cost-per-feature from verified usage records."
      />

      {canPlatform ? (
        <div className="flex flex-wrap gap-3 text-sm">
          <a
            className={!wantPlatform ? "font-semibold text-slate-900 underline" : "text-slate-600 underline"}
            href="/dashboard/ai-costs"
          >
            Organisation view
          </a>
          <a
            className={wantPlatform ? "font-semibold text-slate-900 underline" : "text-slate-600 underline"}
            href="/dashboard/ai-costs?scope=platform"
          >
            Platform view
          </a>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-3 text-sm text-slate-600">
        <a className="underline" href={wantPlatform ? "/dashboard/ai-costs?scope=platform" : "/dashboard/ai-costs"}>
          Current month
        </a>
        <span>Filters use recorded period keys only — figures are never fabricated.</span>
      </div>

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
        <section className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <Metric
            label="Monthly budget"
            value={
              budget.monthly_limit != null
                ? `${String(budget.currency ?? "")} ${String(budget.monthly_limit)}`
                : "Not configured"
            }
          />
          <Metric
            label="Consumed"
            value={String(budget.consumed ?? "0")}
            hint={`Actual ${String(budget.actual_spend ?? "0")} + open reservations ${String(budget.open_reservations ?? "0")}`}
          />
          <Metric label="Remaining" value={budget.remaining != null ? String(budget.remaining) : "—"} />
          <Metric
            label="Utilisation"
            value={budget.utilisation_pct != null ? `${String(budget.utilisation_pct)}%` : "—"}
          />
        </section>
      ) : null}

      <section className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Executions" value={String(totals.execution_count ?? 0)} />
        <Metric
          label="Actual cost"
          value={String(totals.actual_cost ?? "0")}
          hint="Only verified pricing + completed usage"
        />
        <Metric label="Input tokens" value={String(totals.input_tokens ?? 0)} />
        <Metric label="Output tokens" value={String(totals.output_tokens ?? 0)} />
        <Metric label="Cache hits" value={String(totals.cache_hit_count ?? 0)} />
        <Metric label="Premium escalations" value={String(totals.premium_escalation_count ?? 0)} />
        <Metric label="Failed" value={String(totals.failed_count ?? 0)} />
        <Metric label="Rejected (budget)" value={String(totals.rejected_budget_count ?? 0)} />
      </section>

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
          <h2 className="text-lg font-medium text-slate-900">Organisations</h2>
          {((data.organisations as Array<Record<string, unknown>>) ?? []).length === 0 ? (
            <p className="text-sm text-slate-500">No organisation usage in this period.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-slate-500">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Organisation</th>
                    <th className="py-2 pr-4 font-medium">Executions</th>
                    <th className="py-2 pr-4 font-medium">Actual cost</th>
                    <th className="py-2 font-medium">Budget status</th>
                  </tr>
                </thead>
                <tbody>
                  {((data.organisations as Array<Record<string, unknown>>) ?? []).map((row) => {
                    const b = (row.budget as Record<string, unknown>) ?? {};
                    const status = b.budget_exhausted
                      ? "Limit reached"
                      : b.approaching_limit
                        ? "Approaching limit"
                        : "OK";
                    return (
                      <tr key={String(row.organisation_id)} className="border-b border-slate-100">
                        <td className="py-2 pr-4">{String(row.organisation_name ?? row.organisation_id)}</td>
                        <td className="py-2 pr-4">{String(row.execution_count ?? 0)}</td>
                        <td className="py-2 pr-4">{String(row.actual_cost ?? "0")}</td>
                        <td className="py-2">{status}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      <p className="text-xs text-slate-500">Generated at {String(data.generated_at ?? "")}</p>
    </div>
  );
}
