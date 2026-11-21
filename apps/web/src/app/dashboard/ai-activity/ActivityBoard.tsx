"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import {
  Avatar,
  Card,
  DataTable,
  StatusChip,
  Td,
  Th,
  btnPrimary,
  btnSecondary,
  humanize,
  inputClass,
  labelClass,
} from "@/components/ui/primitives";
import {
  FEEDBACK_CATEGORIES,
  canReviewAiFeedback,
  canSubmitAiFeedback,
  formatConfidence,
} from "@/lib/aiActivityView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

type Row = Record<string, unknown>;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function whenLabel(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/London",
  }).format(date);
}

function reviewStatus(row: Row): string {
  const approval = String(row.human_approval_status ?? "");
  if (approval && approval !== "not_applicable") return approval;
  return String(row.execution_status ?? "");
}

function bucket(status: string): "needs_review" | "accepted" | "rejected" | "other" {
  const value = status.toLowerCase();
  if (value.includes("reject")) return "rejected";
  if (value.includes("approv") || value.includes("accept")) return "accepted";
  if (value.includes("review") || value.includes("pending") || value.includes("await")) return "needs_review";
  return "other";
}

function recordLabel(row: Row): string {
  const output = row.output_ref;
  if (output && typeof output === "object") {
    const record = output as Record<string, unknown>;
    const label = record.title || record.label || record.reference || record.name;
    if (typeof label === "string" && label.trim()) return label;
  }
  return "—";
}

function categoryLabel(value: string): string {
  return FEEDBACK_CATEGORIES.find((item) => item.value === value)?.label ?? humanize(value);
}

export function ActivityBoard(props: Props) {
  const canSubmit = canSubmitAiFeedback(props.permissions);
  const canReview = canReviewAiFeedback(props.permissions);
  const [view, setView] = useState<"activity" | "feedback">("activity");
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState<Row | null>(null);
  const [feedbackCategory, setFeedbackCategory] = useState<string>(FEEDBACK_CATEGORIES[0].value);
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
  const [feedbackItems, setFeedbackItems] = useState<Row[]>([]);

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  const loadActivities = useCallback(async () => {
    setError(null);
    setState("loading");
    try {
      const response = await fetch(`${API_BASE}/api/v1/ai-activity?limit=50&offset=0`, { headers: headers() });
      if (!response.ok) {
        setError("AI activity could not be loaded.");
        setState("error");
        return;
      }
      const payload = (await response.json()) as { items: Row[]; total: number };
      setItems(payload.items ?? []);
      setTotal(payload.total ?? 0);
      setState("ready");
    } catch {
      setError("AI activity could not be loaded.");
      setState("error");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.accessToken, props.organisationId, props.role]);

  const loadFeedback = useCallback(async () => {
    if (!canReview) return;
    const response = await fetch(`${API_BASE}/api/v1/ai-activity/feedback?limit=50`, { headers: headers() });
    if (response.ok) {
      const payload = (await response.json()) as { items: Row[] };
      setFeedbackItems(payload.items ?? []);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canReview, props.accessToken, props.organisationId, props.role]);

  useEffect(() => {
    void loadActivities();
  }, [loadActivities]);

  useEffect(() => {
    if (view === "feedback") void loadFeedback();
  }, [view, loadFeedback]);

  async function openActivity(id: string) {
    setFeedbackMsg(null);
    const response = await fetch(`${API_BASE}/api/v1/ai-activity/${id}`, { headers: headers() });
    if (!response.ok) {
      setError("That activity could not be opened.");
      return;
    }
    setSelected((await response.json()) as Row);
  }

  async function submitFeedback() {
    if (!selected || !canSubmit) return;
    setFeedbackMsg(null);
    const response = await fetch(`${API_BASE}/api/v1/ai-activity/${String(selected.id)}/feedback`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ category: feedbackCategory, explanation: feedbackText.trim() || null }),
    });
    if (!response.ok) {
      setFeedbackMsg("Feedback could not be saved.");
      return;
    }
    setFeedbackMsg("Feedback submitted for review.");
    setFeedbackText("");
  }

  async function reviewFeedback(id: string, action: "start_review" | "resolve" | "reject") {
    const response = await fetch(`${API_BASE}/api/v1/ai-activity/feedback/${id}/review`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
        action,
        resolution_notes: action === "resolve" ? "Reviewed. No automatic model change." : null,
        rejection_reason: action === "reject" ? "Not actionable." : null,
      }),
    });
    if (!response.ok) {
      setError("The review could not be saved.");
      return;
    }
    await loadFeedback();
  }

  const needle = query.trim().toLowerCase();
  const visible = items.filter((row) => {
    const status = reviewStatus(row);
    const matchesFilter = filter === "all" || bucket(status) === filter;
    const haystack = `${row.agent_name ?? ""} ${recordLabel(row)}`.toLowerCase();
    return matchesFilter && (!needle || haystack.includes(needle));
  });

  const confidence = selected?.confidence as { kind?: string; label?: string; percentage?: null } | undefined;
  const sources = Array.isArray(selected?.source_refs) ? (selected.source_refs as Record<string, unknown>[]) : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <form
          className="flex min-w-[16rem] flex-1 items-center gap-2"
          onSubmit={(event) => event.preventDefault()}
        >
          <label className="sr-only" htmlFor="activity-search">
            Search feature
          </label>
          <input id="activity-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search feature" className={inputClass} />
        </form>
        <nav aria-label="Review filters" className="flex flex-wrap gap-2">
          {[
            { id: "all", label: "All" },
            { id: "needs_review", label: "Needs review" },
            { id: "accepted", label: "Accepted" },
            { id: "rejected", label: "Rejected" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              aria-pressed={filter === tab.id}
              onClick={() => setFilter(tab.id)}
              className={`inline-flex h-8 items-center rounded-full px-3.5 text-sm font-medium ${
                filter === tab.id ? "bg-brand-700 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {tab.label}
            </button>
          ))}
          {canReview ? (
            <button
              type="button"
              aria-pressed={view === "feedback"}
              onClick={() => setView(view === "feedback" ? "activity" : "feedback")}
              className={`inline-flex h-8 items-center rounded-full px-3.5 text-sm font-medium ${
                view === "feedback" ? "bg-brand-700 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              Feedback
            </button>
          ) : null}
        </nav>
      </div>

      {error ? <ErrorState description={error} /> : null}
      {state === "loading" && items.length === 0 ? <p className="text-sm text-slate-500">Loading AI activity…</p> : null}

      {view === "feedback" ? (
        feedbackItems.length === 0 ? (
          <EmptyState title="No feedback yet" description="Reports that an answer was wrong will appear here for review." />
        ) : (
          <DataTable caption="AI feedback">
            <thead>
              <tr>
                <Th>Category</Th>
                <Th>Explanation</Th>
                <Th>When</Th>
                <Th>Status</Th>
                <Th>Review</Th>
              </tr>
            </thead>
            <tbody>
              {feedbackItems.map((row) => (
                <tr key={String(row.id)}>
                  <Td className="font-semibold text-slate-900">{categoryLabel(String(row.category ?? ""))}</Td>
                  <Td>{String(row.explanation || "—")}</Td>
                  <Td className="whitespace-nowrap text-slate-500">{whenLabel(row.created_at)}</Td>
                  <Td>
                    <StatusChip status={String(row.review_status ?? "")} />
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className={btnSecondary} onClick={() => void reviewFeedback(String(row.id), "start_review")}>
                        Start
                      </button>
                      <button type="button" className={btnPrimary} onClick={() => void reviewFeedback(String(row.id), "resolve")}>
                        Resolve
                      </button>
                      <button type="button" className={btnSecondary} onClick={() => void reviewFeedback(String(row.id), "reject")}>
                        Reject
                      </button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )
      ) : visible.length === 0 && state === "ready" ? (
        <EmptyState
          title={needle || filter !== "all" ? "No matching activity" : "No AI activity yet"}
          description={needle || filter !== "all" ? "Nothing in this list matches that search." : "Suggestions and their review outcome will appear here."}
        />
      ) : (
        <DataTable caption="AI activity">
          <thead>
            <tr>
              <Th>Feature</Th>
              <Th>Record</Th>
              <Th>When</Th>
              <Th>Review</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={String(row.id)} className="hover:bg-slate-50">
                <Td>
                  <button type="button" className="flex items-center gap-3 text-left" onClick={() => void openActivity(String(row.id))}>
                    <Avatar name={String(row.agent_name || "AI")} size="sm" />
                    <span className="font-semibold text-slate-900">{String(row.agent_name || "AI activity")}</span>
                  </button>
                </Td>
                <Td>{recordLabel(row)}</Td>
                <Td className="whitespace-nowrap text-slate-500">{whenLabel(row.created_at ?? row.completed_at)}</Td>
                <Td>
                  <StatusChip status={reviewStatus(row)} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {view === "feedback" ? (feedbackItems.length === 0 ? "0" : `1–${feedbackItems.length}`) : visible.length === 0 ? "0" : `1–${visible.length}`} of{" "}
        {view === "feedback" ? feedbackItems.length : total}
      </p>

      {selected && view === "activity" ? (
        <Card>
          <h2 className="text-base font-semibold text-slate-900">{String(selected.agent_name || "AI activity")}</h2>
          <p className="mt-2 text-sm text-slate-600">Confidence: {formatConfidence(confidence)}</p>
          <div className="mt-4">
            <h3 className="text-sm font-semibold text-slate-900">Sources</h3>
            {sources.length > 0 ? (
              <ul className="mt-2 space-y-1 text-sm text-slate-700">
                {sources.map((source, index) => (
                  <li key={index}>{String(source.title ?? source.label ?? source.type ?? "Source")}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-600">{String(selected.source_notice || "No sources were recorded for this result.")}</p>
            )}
          </div>
          {canSubmit ? (
            <form
              className="mt-4 space-y-3"
              onSubmit={(event) => {
                event.preventDefault();
                void submitFeedback();
              }}
            >
              <div className="space-y-1.5">
                <label className={labelClass} htmlFor="feedback-category">
                  What was wrong
                </label>
                <select id="feedback-category" className={inputClass} value={feedbackCategory} onChange={(event) => setFeedbackCategory(event.target.value)}>
                  {FEEDBACK_CATEGORIES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className={labelClass} htmlFor="feedback-note">
                  Explanation
                </label>
                <textarea id="feedback-note" className={`${inputClass} h-auto py-2`} rows={3} value={feedbackText} onChange={(event) => setFeedbackText(event.target.value)} />
              </div>
              <button type="submit" className={btnPrimary}>
                Send feedback
              </button>
              {feedbackMsg ? <p className="text-sm text-slate-600">{feedbackMsg}</p> : null}
            </form>
          ) : null}
          <button type="button" className={`${btnSecondary} mt-4`} onClick={() => setSelected(null)}>
            Close
          </button>
        </Card>
      ) : null}
    </div>
  );
}
