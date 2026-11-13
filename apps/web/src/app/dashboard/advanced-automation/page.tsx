import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  fetchAdvancedAutomationDashboard,
  fetchWorkflowTemplates,
  fetchWorkflows,
} from "@/lib/advancedAutomationApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = [
  "advanced_automation.read",
  "advanced_automation.manage",
  "advanced_automation.reports",
  "automation.rules.read",
  "automation.rules.manage",
];

export default async function AdvancedAutomationPage() {
  const session = await requireAuthenticatedSession("/dashboard/advanced-automation");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  const auth = { accessToken: token, organisationId: orgId, role: session.authorization?.active_role };
  let dash: Record<string, unknown> = {};
  let templates: Record<string, unknown>[] = [];
  let workflows: Record<string, unknown>[] = [];

  try {
    dash = await fetchAdvancedAutomationDashboard(auth);
    templates = await fetchWorkflowTemplates(auth);
    workflows = await fetchWorkflows(auth);
  } catch {
    return (
      <ErrorState description="Advanced automation is disabled until ADVANCED_AUTOMATION_GLOBAL_ENABLED and organisation settings are approved." />
    );
  }

  const stats = [
    { label: "Intelligent workflows", value: String(dash.intelligent_workflows_total ?? "0") },
    { label: "Active", value: String(dash.intelligent_workflows_active ?? "0") },
    { label: "Draft", value: String(dash.intelligent_workflows_draft ?? "0") },
    { label: "Running", value: String(dash.executions_running ?? "0") },
    { label: "Failed", value: String(dash.executions_failed ?? "0") },
    { label: "Pending approvals", value: String(dash.pending_approvals ?? "0") },
    { label: "F6.3 rules", value: String(dash.total_rules ?? "0") },
    { label: "Success rate %", value: String(dash.automation_success_rate_percent ?? "—") },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Advanced workflows (F8.11)</h1>
          <p className="mt-1 text-sm text-slate-600">
            Intelligent workflows extend F6.3 automation and F2.13 approvals. Use the classic automation UI for rule engine jobs.
          </p>
          {typeof dash.disclaimer === "string" ? <p className="mt-2 text-xs text-amber-800">{dash.disclaimer}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <Link className="rounded border border-slate-200 bg-white px-3 py-1.5 hover:bg-slate-50" href="/dashboard/automation">
            F6.3 automation
          </Link>
          <Link className="rounded border border-slate-200 bg-white px-3 py-1.5 hover:bg-slate-50" href="/dashboard/integration-hub">
            Integration hub
          </Link>
        </div>
      </header>
      <section className="grid gap-3 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs uppercase tracking-wide text-slate-500">{s.label}</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{s.value}</div>
          </div>
        ))}
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="font-medium text-slate-800">Workflow templates</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {templates.slice(0, 12).map((t) => (
              <li key={String(t.key)} className="py-2">
                <span className="font-medium">{String(t.name)}</span>
                <span className="ml-2 text-slate-400">{String(t.key)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">Copy templates via API when creating workflows. Visual drag-and-drop builder is planned.</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="font-medium text-slate-800">Your workflows</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {workflows.length === 0 ? (
              <li className="py-2 text-slate-500">No workflows yet.</li>
            ) : (
              workflows.map((w) => (
                <li key={String(w.id)} className="flex justify-between py-2">
                  <span>{String(w.name)}</span>
                  <span className="text-slate-500">{String(w.status)}</span>
                </li>
              ))
            )}
          </ul>
        </div>
      </section>
    </div>
  );
}
