"use client";

import { useCallback, useEffect, useState } from "react";
import { StatusChip } from "@/components/ui/primitives";
import {
  CONFIDENCE_UNAVAILABLE,
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

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Activity = Record<string, unknown>;
type Feedback = Record<string, unknown>;

export function AiActivityPanel(props: Props) {
  const [tab, setTab] = useState<"activity" | "feedback">("activity");
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<Activity[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [featureFilter, setFeatureFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<Activity | null>(null);
  const [feedbackCategory, setFeedbackCategory] = useState<string>(FEEDBACK_CATEGORIES[0].value);
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
  const [feedbackItems, setFeedbackItems] = useState<Feedback[]>([]);
  const [feedbackStats, setFeedbackStats] = useState<Record<string, unknown> | null>(null);
  const canSubmit = canSubmitAiFeedback(props.permissions);
  const canReview = canReviewAiFeedback(props.permissions);
  const limit = 20;

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  const loadActivities = useCallback(
    async (nextOffset = 0) => {
      setError(null);
      setState("loading");
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(nextOffset),
      });
      if (featureFilter) params.set("feature_id", featureFilter);
      if (statusFilter) params.set("execution_status", statusFilter);
      try {
        const response = await fetch(`${API_BASE}/api/v1/ai-activity?${params}`, {
          headers: headers(),
        });
        if (!response.ok) {
          setError(await response.text());
          setState("error");
          return;
        }
        const payload = (await response.json()) as {
          items: Activity[];
          total: number;
        };
        setItems(payload.items ?? []);
        setTotal(payload.total ?? 0);
        setOffset(nextOffset);
        setState("ready");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load AI activity");
        setState("error");
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [featureFilter, statusFilter, props.accessToken, props.organisationId, props.role],
  );

  const loadFeedback = useCallback(async () => {
    if (!canReview) return;
    const response = await fetch(`${API_BASE}/api/v1/ai-activity/feedback?limit=50`, {
      headers: headers(),
    });
    if (response.ok) {
      const payload = (await response.json()) as { items: Feedback[] };
      setFeedbackItems(payload.items ?? []);
    }
    const stats = await fetch(`${API_BASE}/api/v1/ai-activity/feedback/stats`, {
      headers: headers(),
    });
    if (stats.ok) {
      setFeedbackStats((await stats.json()) as Record<string, unknown>);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canReview, props.accessToken, props.organisationId, props.role]);

  useEffect(() => {
    void loadActivities(0);
  }, [loadActivities]);

  useEffect(() => {
    if (tab === "feedback") void loadFeedback();
  }, [tab, loadFeedback]);

  async function openActivity(id: string) {
    setFeedbackMsg(null);
    const response = await fetch(`${API_BASE}/api/v1/ai-activity/${id}`, {
      headers: headers(),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    setSelected((await response.json()) as Activity);
  }

  async function submitFeedback() {
    if (!selected || !canSubmit) return;
    setFeedbackMsg(null);
    const response = await fetch(
      `${API_BASE}/api/v1/ai-activity/${String(selected.id)}/feedback`,
      {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          category: feedbackCategory,
          explanation: feedbackText.trim() || null,
        }),
      },
    );
    if (!response.ok) {
      setFeedbackMsg(await response.text());
      return;
    }
    setFeedbackMsg("Feedback submitted for human review.");
    setFeedbackText("");
  }

  async function reviewFeedback(id: string, action: "start_review" | "resolve" | "reject") {
    const response = await fetch(`${API_BASE}/api/v1/ai-activity/feedback/${id}/review`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
        action,
        resolution_notes: action === "resolve" ? "Reviewed — no automatic model change." : null,
        rejection_reason: action === "reject" ? "Not actionable / duplicate signal" : null,
      }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    await loadFeedback();
  }

  const confidence = selected?.confidence as
    | { kind?: string; label?: string; percentage?: null }
    | undefined;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={`inline-flex h-8 items-center rounded-full px-3.5 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
            tab === "activity" ? "bg-brand-700 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
          onClick={() => setTab("activity")}
        >
          Activity history
        </button>
        {canReview ? (
          <button
            type="button"
            className={`inline-flex h-8 items-center rounded-full px-3.5 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
              tab === "feedback" ? "bg-brand-700 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
            }`}
            onClick={() => setTab("feedback")}
          >
            Feedback review
          </button>
        ) : null}
      </div>

      {error ? <p className="text-sm text-red-800">{error}</p> : null}

      {tab === "activity" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-sm text-slate-700">
              Feature
              <input
                className="ml-2 block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
                value={featureFilter}
                onChange={(e) => setFeatureFilter(e.target.value)}
                placeholder="ai.agent…"
              />
            </label>
            <label className="text-sm text-slate-700">
              Status
              <select
                className="ml-2 block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">Any</option>
                <option value="completed">completed</option>
                <option value="failed">failed</option>
                <option value="rejected_budget">rejected_budget</option>
              </select>
            </label>
            <button
              type="button"
              className="inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
              onClick={() => void loadActivities(0)}
            >
              Apply filters
            </button>
          </div>

          {state === "loading" ? <p className="text-sm text-slate-600">Loading…</p> : null}
          {state === "ready" && items.length === 0 ? (
            <p className="text-sm text-slate-600">No AI activity records yet.</p>
          ) : null}

          <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
            {items.map((row) => (
              <li key={String(row.id)} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div>
                  <p className="font-medium text-slate-900">{String(row.agent_name)}</p>
                  <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span>{String(row.created_at ?? row.completed_at ?? "")}</span>
                    <StatusChip status={String(row.execution_status)} />
                    <span>{row.sources_available ? "sources available" : "no sources"}</span>
                  </p>
                </div>
                <button
                  type="button"
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                  onClick={() => void openActivity(String(row.id))}
                >
                  Open
                </button>
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-2 text-sm">
            <button
              type="button"
              disabled={offset <= 0}
              className="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-40"
              onClick={() => void loadActivities(Math.max(0, offset - limit))}
            >
              Previous
            </button>
            <span>
              {offset + 1}–{Math.min(offset + limit, total)} of {total}
            </span>
            <button
              type="button"
              disabled={offset + limit >= total}
              className="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-40"
              onClick={() => void loadActivities(offset + limit)}
            >
              Next
            </button>
          </div>

          {selected ? (
            <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/50 p-4">
              <h3 className="font-semibold text-slate-900">{String(selected.agent_name)}</h3>
              <p className="text-sm text-slate-700">
                Status: {String(selected.execution_status)} · Prompt:{" "}
                {String(selected.prompt_id ?? "—")} @ {String(selected.prompt_version ?? "—")}
              </p>
              <p className="text-sm font-medium text-slate-900">
                Confidence: {formatConfidence(confidence)}
              </p>
              {confidence?.kind === "unavailable" || !confidence ? (
                <p className="text-xs text-slate-600">
                  {CONFIDENCE_UNAVAILABLE}. This result requires human review where decisions matter.
                  No calibrated percentage is shown.
                </p>
              ) : (
                <p className="text-xs text-slate-600">
                  Signal kind: {String(confidence.kind)}. Not a calibrated accuracy score.
                </p>
              )}

              <div>
                <h4 className="text-sm font-semibold text-slate-900">Source references</h4>
                {Array.isArray(selected.source_refs) && selected.source_refs.length > 0 ? (
                  <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
                    {(selected.source_refs as Record<string, unknown>[]).map((ref, idx) => (
                      <li key={idx}>
                        {String(ref.type ?? "source")}: {String(ref.title ?? ref.label ?? ref.id ?? "—")}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-600">
                    {String(selected.source_notice ?? "No available source references for this AI result.")}
                  </p>
                )}
              </div>

              <p className="text-sm text-slate-700">
                Human approval: {String(selected.human_approval_status)}
              </p>

              {canSubmit ? (
                <div className="space-y-2 border-t border-amber-200 pt-3">
                  <h4 className="text-sm font-semibold text-slate-900">Report wrong answer</h4>
                  <select
                    className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
                    value={feedbackCategory}
                    onChange={(e) => setFeedbackCategory(e.target.value)}
                  >
                    {FEEDBACK_CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                  <textarea
                    className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
                    rows={3}
                    maxLength={2000}
                    placeholder="Optional short explanation"
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                  />
                  <button
                    type="button"
                    className="inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
                    onClick={() => void submitFeedback()}
                  >
                    Submit feedback
                  </button>
                  {feedbackMsg ? <p className="text-sm text-slate-700">{feedbackMsg}</p> : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="space-y-4">
          {feedbackStats ? (
            <p className="text-sm text-slate-600">
              {String(feedbackStats.note)} Categories:{" "}
              {JSON.stringify(feedbackStats.by_category ?? {})}
            </p>
          ) : null}
          <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
            {feedbackItems.map((fb) => (
              <li key={String(fb.id)} className="space-y-2 p-3">
                <p className="text-sm font-medium text-slate-900">
                  {String(fb.category)} · {String(fb.review_status)}
                </p>
                <p className="text-xs text-slate-500">{String(fb.explanation ?? "—")}</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                    onClick={() => void openActivity(String(fb.activity_id))}
                  >
                    Open activity
                  </button>
                  <button
                    type="button"
                    className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                    onClick={() => void reviewFeedback(String(fb.id), "start_review")}
                  >
                    Mark under review
                  </button>
                  <button
                    type="button"
                    className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                    onClick={() => void reviewFeedback(String(fb.id), "resolve")}
                  >
                    Resolve
                  </button>
                  <button
                    type="button"
                    className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                    onClick={() => void reviewFeedback(String(fb.id), "reject")}
                  >
                    Reject
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
