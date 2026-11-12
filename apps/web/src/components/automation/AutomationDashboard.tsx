"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  createAutomationRule,
  deleteAutomationRule,
  fetchAutomationComplianceIssues,
  fetchAutomationDashboard,
  fetchAutomationEscalations,
  fetchAutomationRules,
  fetchAutomationRuns,
  retryAutomationRun,
  runAutomationRule,
  updateAutomationEscalation,
  updateAutomationRule,
} from "@/lib/automationApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
};

const TRIGGER_OPTIONS = [
  "appointment_upcoming",
  "appointment_overdue",
  "support_plan_review_upcoming",
  "support_plan_review_overdue",
  "task_pending",
  "task_overdue",
  "inspection_upcoming",
  "inspection_overdue",
  "document_expiry",
  "complaint_action_required",
  "maintenance_scheduled",
  "complaint_overdue",
  "maintenance_high_priority",
  "followup_missed",
  "task_overdue_escalation",
  "inspection_missed",
  "safeguarding_followup_overdue",
  "compliance_scheduled_sweep",
];

export function AutomationDashboard({ accessToken, organisationId, role, canManage }: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [rules, setRules] = useState<Record<string, unknown>[]>([]);
  const [runs, setRuns] = useState<Record<string, unknown>[]>([]);
  const [escalations, setEscalations] = useState<Record<string, unknown>[]>([]);
  const [issues, setIssues] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [pending, startTransition] = useTransition();

  const [name, setName] = useState("Overdue complaint escalation");
  const [description, setDescription] = useState("Escalate open complaints past response deadline");
  const [ruleCategory, setRuleCategory] = useState("escalation");
  const [trigger, setTrigger] = useState("complaint_overdue");
  const [actionType, setActionType] = useState("escalate_record");
  const [frequency, setFrequency] = useState("daily");
  const [leadDays, setLeadDays] = useState(3);

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        const [d, r, rn, e, i] = await Promise.all([
          fetchAutomationDashboard(auth),
          fetchAutomationRules({
            ...auth,
            category: category || undefined,
            search: search || undefined,
          }),
          fetchAutomationRuns({ ...auth, status: statusFilter || undefined }),
          fetchAutomationEscalations({ ...auth, status: "open" }),
          fetchAutomationComplianceIssues({ ...auth, status: "open" }),
        ]);
        setDash(d);
        setRules(r.items);
        setRuns(rn.items);
        setEscalations(e.items);
        setIssues(i.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load automation");
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, statusFilter]);

  const onCreate = () => {
    startTransition(async () => {
      try {
        const action_config: Record<string, unknown> = {
          channels: ["in_app", "email"],
          recipient_role: "organisation_admin",
          require_human_approval: actionType === "create_approval_request",
        };
        if (actionType === "escalate_record") {
          action_config.escalation_level = 1;
          action_config.severity = "high";
        }
        await createAutomationRule(auth, {
          name,
          description,
          category: ruleCategory,
          trigger_condition: trigger,
          trigger_config: { lead_days: leadDays },
          action_type: actionType,
          action_config,
          frequency,
          is_enabled: true,
        });
        refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Create failed");
      }
    });
  };

  const cards = [
    { label: "Total rules", value: dash?.total_rules },
    { label: "Active", value: dash?.active_rules },
    { label: "Disabled", value: dash?.disabled_rules },
    { label: "Succeeded", value: dash?.successful_executions },
    { label: "Failed", value: dash?.failed_executions },
    { label: "Pending reminders", value: dash?.pending_reminders },
    { label: "Sent reminders", value: dash?.sent_reminders },
    { label: "Active escalations", value: dash?.active_escalations },
    { label: "Open compliance issues", value: dash?.open_compliance_issues },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Automation rules</h1>
        <p className="mt-1 text-sm text-slate-600">
          Reminders, escalations and compliance sweeps from live records. Sensitive housing, tenancy and
          employment decisions always require human approval.
        </p>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {pending && !dash ? <p className="text-sm text-slate-500">Loading…</p> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <div key={c.label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-slate-500">{c.label}</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{String(c.value ?? "—")}</div>
          </div>
        ))}
      </div>

      {canManage ? (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-medium text-slate-800">Create rule</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-sm">
              Name
              <input className="mt-1 w-full rounded border px-2 py-1.5" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="text-sm">
              Description
              <input
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <label className="text-sm">
              Category
              <select
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={ruleCategory}
                onChange={(e) => {
                  const v = e.target.value;
                  setRuleCategory(v);
                  if (v === "reminder") setActionType("create_reminder");
                  if (v === "escalation") setActionType("escalate_record");
                  if (v === "compliance_sweep") {
                    setActionType("run_compliance_sweep");
                    setTrigger("compliance_scheduled_sweep");
                  }
                }}
              >
                <option value="reminder">reminder</option>
                <option value="escalation">escalation</option>
                <option value="compliance_sweep">compliance_sweep</option>
              </select>
            </label>
            <label className="text-sm">
              Trigger
              <select className="mt-1 w-full rounded border px-2 py-1.5" value={trigger} onChange={(e) => setTrigger(e.target.value)}>
                {TRIGGER_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              Action
              <select
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
              >
                <option value="create_reminder">create_reminder</option>
                <option value="escalate_record">escalate_record</option>
                <option value="run_compliance_sweep">run_compliance_sweep</option>
                <option value="create_approval_request">create_approval_request</option>
              </select>
            </label>
            <label className="text-sm">
              Frequency
              <select
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
              >
                <option value="hourly">hourly</option>
                <option value="daily">daily</option>
                <option value="weekly">weekly</option>
                <option value="manual">manual</option>
              </select>
            </label>
            <label className="text-sm">
              Lead days
              <input
                type="number"
                min={0}
                max={90}
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={leadDays}
                onChange={(e) => setLeadDays(Number(e.target.value))}
              />
            </label>
          </div>
          <button
            type="button"
            disabled={pending}
            onClick={onCreate}
            className="rounded bg-teal-800 px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            Create rule
          </button>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <input
          className="rounded border px-2 py-1.5 text-sm"
          placeholder="Search rules"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="rounded border px-2 py-1.5 text-sm" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          <option value="reminder">reminder</option>
          <option value="escalation">escalation</option>
          <option value="compliance_sweep">compliance_sweep</option>
        </select>
        <button type="button" className="rounded border px-3 py-1.5 text-sm" onClick={refresh}>
          Apply
        </button>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Rules</h2>
        {!rules.length ? (
          <p className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">No rules yet.</p>
        ) : (
          <ul className="space-y-2">
            {rules.map((rule) => (
              <li key={String(rule.id)} className="rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-900">{String(rule.name)}</div>
                    <div className="text-slate-600">
                      {String(rule.category)} · {String(rule.trigger_condition)} · {String(rule.action_type)} ·{" "}
                      {String(rule.frequency)} · {rule.is_enabled ? "enabled" : "disabled"}
                    </div>
                    <div className="text-xs text-slate-500">
                      last {String(rule.last_run_at ?? "—")} · next {String(rule.next_run_at ?? "—")}
                    </div>
                  </div>
                  {canManage ? (
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded border px-2 py-1"
                        onClick={() =>
                          startTransition(async () => {
                            await updateAutomationRule(auth, String(rule.id), {
                              is_enabled: !rule.is_enabled,
                            });
                            refresh();
                          })
                        }
                      >
                        {rule.is_enabled ? "Disable" : "Enable"}
                      </button>
                      <button
                        type="button"
                        className="rounded border px-2 py-1"
                        onClick={() =>
                          startTransition(async () => {
                            await runAutomationRule(auth, String(rule.id));
                            refresh();
                          })
                        }
                      >
                        Run now
                      </button>
                      <button
                        type="button"
                        className="rounded border border-red-300 px-2 py-1 text-red-800"
                        onClick={() =>
                          startTransition(async () => {
                            await deleteAutomationRule(auth, String(rule.id));
                            refresh();
                          })
                        }
                      >
                        Delete
                      </button>
                    </div>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-medium text-slate-800">Execution history</h2>
          <select
            className="rounded border px-2 py-1 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">all</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
            <option value="skipped">skipped</option>
          </select>
        </div>
        {!runs.length ? (
          <p className="text-sm text-slate-500">No runs yet.</p>
        ) : (
          <ul className="space-y-2">
            {runs.map((run) => (
              <li key={String(run.id)} className="flex flex-wrap items-center justify-between gap-2 rounded border bg-white p-3 text-sm">
                <div>
                  <div>
                    {String(run.status)} · attempts {String(run.attempt_count)}
                    {run.requires_human_approval ? " · human approval flagged" : ""}
                  </div>
                  <div className="text-slate-600">{String(run.error_message ?? JSON.stringify(run.result_summary ?? {}))}</div>
                </div>
                {canManage && run.status === "failed" ? (
                  <button
                    type="button"
                    className="rounded border px-2 py-1"
                    onClick={() =>
                      startTransition(async () => {
                        await retryAutomationRun(auth, String(run.id));
                        refresh();
                      })
                    }
                  >
                    Retry
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Active escalations</h2>
        {!escalations.length ? (
          <p className="text-sm text-slate-500">No open escalations.</p>
        ) : (
          <ul className="space-y-2">
            {escalations.map((esc) => (
              <li key={String(esc.id)} className="rounded border bg-white p-3 text-sm">
                <div className="font-medium">{String(esc.reason)}</div>
                <div className="text-slate-600">
                  {String(esc.resource_type)} {String(esc.resource_id)} · level {String(esc.escalation_level)} ·{" "}
                  {String(esc.severity)}
                </div>
                <div className="mt-2 flex gap-2">
                  {["acknowledged", "resolved", "dismissed"].map((s) => (
                    <button
                      key={s}
                      type="button"
                      className="rounded border px-2 py-1 text-xs capitalize"
                      onClick={() =>
                        startTransition(async () => {
                          await updateAutomationEscalation(auth, String(esc.id), s);
                          refresh();
                        })
                      }
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Open compliance issues</h2>
        {!issues.length ? (
          <p className="text-sm text-slate-500">No open compliance issues from automation sweeps.</p>
        ) : (
          <ul className="space-y-2">
            {issues.map((issue) => (
              <li key={String(issue.id)} className="rounded border bg-white p-3 text-sm">
                <div className="font-medium">{String(issue.title)}</div>
                <div className="text-slate-600">
                  {String(issue.issue_type)} · {String(issue.severity)} · {String(issue.detected_at)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
