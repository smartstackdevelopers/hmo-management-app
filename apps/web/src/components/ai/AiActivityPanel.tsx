"use client";

import { useCallback, useEffect, useState } from "react";
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
          className={`rounded-md px-3 py-1.5 text-sm ${
            tab === "activity" ? "bg-forest-800 text-white" : "border border-forest-200"
          }`}
          onClick={() => setTab("activity")}
        >
          Activity history
        </button>
        {canReview ? (
          <button
            type="button"
            className={`rounded-md px-3 py-1.5 text-sm ${
              tab === "feedback" ? "bg-forest-800 text-white" : "border border-forest-200"
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
            <label className="text-sm text-forest-800">
              Feature
              <input
                className="ml-2 rounded-md border border-forest-200 p-1 text-sm"
                value={featureFilter}
                onChange={(e) => setFeatureFilter(e.target.value)}
                placeholder="ai.agent…"
              />
            </label>
            <label className="text-sm text-forest-800">
              Status
              <select
                className="ml-2 rounded-md border border-forest-200 p-1 text-sm"
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
              className="rounded-md bg-forest-800 px-3 py-1.5 text-sm text-white"
              onClick={() => void loadActivities(0)}
            >
              Apply filters
            </button>
          </div>

          {state === "loading" ? <p className="text-sm text-forest-700">Loading…</p> : null}
          {state === "ready" && items.length === 0 ? (
            <p className="text-sm text-forest-700">No AI activity records yet.</p>
          ) : null}

          <ul className="divide-y divide-forest-100 rounded-lg border border-forest-100 bg-white">
            {items.map((row) => (
              <li key={String(row.id)} className="flex flex-wrap items-center justify-between gap-2 p-3">
                <div>
                  <p className="font-medium text-forest-900">{String(row.agent_name)}</p>
                  <p className="text-xs text-forest-600">
                    {String(row.created_at ?? row.completed_at ?? "")} · {String(row.execution_status)} ·{" "}
                    {row.sources_available ? "sources available" : "no sources"}
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-md border border-forest-200 px-2 py-1 text-sm"
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
              className="rounded-md border border-forest-200 px-2 py-1 disabled:opacity-40"
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
              className="rounded-md border border-forest-200 px-2 py-1 disabled:opacity-40"
              onClick={() => void loadActivities(offset + limit)}
            >
              Next
            </button>
          </div>

          {selected ? (
            <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/50 p-4">
              <h3 className="font-semibold text-forest-900">{String(selected.agent_name)}</h3>
              <p className="text-sm text-forest-800">
                Status: {String(selected.execution_status)} · Prompt:{" "}
                {String(selected.prompt_id ?? "—")} @ {String(selected.prompt_version ?? "—")}
              </p>
              <p className="text-sm font-medium text-forest-900">
                Confidence: {formatConfidence(confidence)}
              </p>
              {confidence?.kind === "unavailable" || !confidence ? (
                <p className="text-xs text-forest-700">
                  {CONFIDENCE_UNAVAILABLE}. This result requires human review where decisions matter.
                  No calibrated percentage is shown.
                </p>
              ) : (
                <p className="text-xs text-forest-700">
                  Signal kind: {String(confidence.kind)}. Not a calibrated accuracy score.
                </p>
              )}

              <div>
                <h4 className="text-sm font-semibold text-forest-900">Source references</h4>
                {Array.isArray(selected.source_refs) && selected.source_refs.length > 0 ? (
                  <ul className="mt-1 list-disc pl-5 text-sm text-forest-800">
                    {(selected.source_refs as Record<string, unknown>[]).map((ref, idx) => (
                      <li key={idx}>
                        {String(ref.type ?? "source")}: {String(ref.title ?? ref.label ?? ref.id ?? "—")}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-forest-700">
                    {String(selected.source_notice ?? "No available source references for this AI result.")}
                  </p>
                )}
              </div>

              <p className="text-sm text-forest-800">
                Human approval: {String(selected.human_approval_status)}
              </p>

              {canSubmit ? (
                <div className="space-y-2 border-t border-amber-200 pt-3">
                  <h4 className="text-sm font-semibold text-forest-900">Report wrong answer</h4>
                  <select
                    className="w-full rounded-md border border-forest-200 p-2 text-sm"
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
                    className="w-full rounded-md border border-forest-200 p-2 text-sm"
                    rows={3}
                    maxLength={2000}
                    placeholder="Optional short explanation"
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                  />
                  <button
                    type="button"
                    className="rounded-md bg-forest-800 px-3 py-1.5 text-sm text-white"
                    onClick={() => void submitFeedback()}
                  >
                    Submit feedback
                  </button>
                  {feedbackMsg ? <p className="text-sm text-forest-800">{feedbackMsg}</p> : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="space-y-4">
          {feedbackStats ? (
            <p className="text-sm text-forest-700">
              {String(feedbackStats.note)} Categories:{" "}
              {JSON.stringify(feedbackStats.by_category ?? {})}
            </p>
          ) : null}
          <ul className="divide-y divide-forest-100 rounded-lg border border-forest-100 bg-white">
            {feedbackItems.map((fb) => (
              <li key={String(fb.id)} className="space-y-2 p-3">
                <p className="text-sm font-medium text-forest-900">
                  {String(fb.category)} · {String(fb.review_status)}
                </p>
                <p className="text-xs text-forest-600">{String(fb.explanation ?? "—")}</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-md border border-forest-200 px-2 py-1 text-xs"
                    onClick={() => void openActivity(String(fb.activity_id))}
                  >
                    Open activity
                  </button>
                  <button
                    type="button"
                    className="rounded-md border border-forest-200 px-2 py-1 text-xs"
                    onClick={() => void reviewFeedback(String(fb.id), "start_review")}
                  >
                    Mark under review
                  </button>
                  <button
                    type="button"
                    className="rounded-md border border-forest-200 px-2 py-1 text-xs"
                    onClick={() => void reviewFeedback(String(fb.id), "resolve")}
                  >
                    Resolve
                  </button>
                  <button
                    type="button"
                    className="rounded-md border border-forest-200 px-2 py-1 text-xs"
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
