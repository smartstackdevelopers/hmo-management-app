"use client";

import { useState } from "react";
import {
  REPORT_DRAFT_NOTICE,
  canReviewReportDrafts,
} from "@/lib/reportDraftsView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function ReportDraftsPanel(props: Props) {
  const [periodType, setPeriodType] = useState<"weekly" | "monthly">("weekly");
  const [state, setState] = useState<"idle" | "loading" | "error" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, unknown> | null>(null);
  const [editedBody, setEditedBody] = useState("");
  const canReview = canReviewReportDrafts(props.permissions);

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  async function generate(regenerate = false) {
    setError(null);
    setState("loading");
    try {
      const response = await fetch(`${API_BASE}/api/v1/report-drafts`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ period_type: periodType, regenerate }),
      });
      if (!response.ok) {
        setError(await response.text());
        setState("error");
        return;
      }
      const payload = (await response.json()) as Record<string, unknown>;
      setDraft(payload);
      setEditedBody(String(payload.display_body ?? payload.narrative_text ?? ""));
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report draft failed");
      setState("error");
    }
  }

  async function saveEdit() {
    if (!draft) return;
    const response = await fetch(`${API_BASE}/api/v1/report-drafts/${String(draft.id)}`, {
      method: "PATCH",
      headers: headers(),
      body: JSON.stringify({ edited_body: editedBody }),
    });
    if (!response.ok) {
      setError(await response.text());
      setState("error");
      return;
    }
    setDraft((await response.json()) as Record<string, unknown>);
  }

  async function review(decision: "approve" | "reject") {
    if (!draft) return;
    const response = await fetch(`${API_BASE}/api/v1/report-drafts/${String(draft.id)}/review`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ decision, review_comment: null }),
    });
    if (!response.ok) {
      setError(await response.text());
      setState("error");
      return;
    }
    setDraft((await response.json()) as Record<string, unknown>);
  }

  return (
    <section className="space-y-4 rounded-lg border border-amber-200 bg-amber-50/40 p-4">
      <h2 className="text-lg font-semibold text-forest-900">Report drafts</h2>
      <p className="text-sm font-medium text-amber-950">{REPORT_DRAFT_NOTICE}</p>
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-forest-800">
          Period
          <select
            className="ml-2 rounded-md border border-forest-200 p-1 text-sm"
            value={periodType}
            onChange={(event) => setPeriodType(event.target.value as "weekly" | "monthly")}
          >
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
        <button
          type="button"
          className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
          disabled={state === "loading"}
          onClick={() => void generate(false)}
        >
          {state === "loading" ? "Generating…" : "Generate draft"}
        </button>
        <button
          type="button"
          className="rounded-md border border-forest-300 px-3 py-2 text-sm"
          disabled={state === "loading"}
          onClick={() => void generate(true)}
        >
          Regenerate
        </button>
      </div>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {draft ? (
        <div className="space-y-3">
          <p className="text-sm text-forest-800">
            {String(draft.period_type)} · {String(draft.period_start)} → {String(draft.period_end)} · status{" "}
            {String(draft.status)} · AI {String(draft.ai_status)}
          </p>
          <pre className="overflow-auto rounded-md bg-white/70 p-2 text-xs">
            {JSON.stringify(draft.metrics ?? {}, null, 2)}
          </pre>
          {canReview && draft.status === "draft" ? (
            <>
              <textarea
                className="w-full rounded-md border border-forest-200 p-2 text-sm"
                rows={8}
                value={editedBody}
                onChange={(event) => setEditedBody(event.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-md border border-forest-300 px-3 py-1.5 text-sm"
                  onClick={() => void saveEdit()}
                >
                  Save edits
                </button>
                <button
                  type="button"
                  className="rounded-md bg-teal-800 px-3 py-1.5 text-sm text-white"
                  onClick={() => void review("approve")}
                >
                  Approve (no distribution)
                </button>
                <button
                  type="button"
                  className="rounded-md border border-forest-400 px-3 py-1.5 text-sm"
                  onClick={() => void review("reject")}
                >
                  Reject
                </button>
              </div>
            </>
          ) : (
            <pre className="whitespace-pre-wrap rounded-md bg-white/70 p-2 text-sm">
              {String(draft.display_body ?? draft.narrative_text ?? "No narrative available.")}
            </pre>
          )}
        </div>
      ) : null}
    </section>
  );
}
