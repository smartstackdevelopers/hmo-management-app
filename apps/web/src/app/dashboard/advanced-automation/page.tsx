import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatCard, StatGrid, StatusChip, Td, Th, btnSecondary } from "@/components/ui/primitives";
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
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see automation." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so automation can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/advanced-automation" />;
  }

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
      <ErrorState
        title="Automation unavailable"
        description="Automation isn't switched on for this organisation yet."
        retryHref="/dashboard/advanced-automation"
      />
    );
  }

  const stats = [
    { label: "Intelligent workflows", value: String(dash.intelligent_workflows_total ?? "0") },
    { label: "Active", value: String(dash.intelligent_workflows_active ?? "0") },
    { label: "Draft", value: String(dash.intelligent_workflows_draft ?? "0") },
    { label: "Running", value: String(dash.executions_running ?? "0") },
    { label: "Failed", value: String(dash.executions_failed ?? "0") },
    { label: "Pending approvals", value: String(dash.pending_approvals ?? "0") },
    { label: "Rules", value: String(dash.total_rules ?? "0") },
    { label: "Success rate %", value: String(dash.automation_success_rate_percent ?? "—") },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Insights / Automation"
        title="Automation rules"
        description="Let routine work happen automatically — always reviewable."
        actions={
          <>
            <Link className={btnSecondary} href="/dashboard/automation">
              Rule engine
            </Link>
            <Link className={btnSecondary} href="/dashboard/integration-hub">
              Integration hub
            </Link>
          </>
        }
      />
      {typeof dash.disclaimer === "string" ? (
        <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{dash.disclaimer}</p>
      ) : null}
      <StatGrid>
        {stats.map((s) => (
          <StatCard key={s.label} label={s.label} value={s.value} />
        ))}
      </StatGrid>
      {workflows.length === 0 ? (
        <EmptyState title="No workflows yet" description="Workflows you create will appear here with their current status." />
      ) : (
        <DataTable caption="Workflows">
          <thead>
            <tr>
              <Th>Workflow</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {workflows.map((workflow) => (
              <tr key={String(workflow.id)}>
                <Td className="font-semibold text-slate-900">{String(workflow.name)}</Td>
                <Td>
                  <StatusChip status={String(workflow.status)} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {workflows.length === 0 ? "0" : `1–${workflows.length}`} of {workflows.length}
        {templates.length > 0 ? ` · ${templates.length} template${templates.length === 1 ? "" : "s"} available` : ""}
      </p>
    </div>
  );
}
