"use client";

import { useState } from "react";
import {
  AI_LIMITATION_NOTICE,
  analysisLayoutClass,
  canReviewHousingApplicationAnalysis,
  findingLabel,
  outcomeLabel,
} from "@/lib/housingApplicationAnalysisView";

type Props = {
  applicationId: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function HousingApplicationAnalysisPanel(props: Props) {
  const [state, setState] = useState<"idle" | "loading" | "error" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [comment, setComment] = useState("");
  const canReview = canReviewHousingApplicationAnalysis(props.permissions);

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  async function analyse(force: boolean) {
    setError(null);
    setState("loading");
    try {
      const response = await fetch(`${API_BASE}/api/v1/housing-application-analyses`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ application_id: props.applicationId, force }),
      });
      if (!response.ok) {
        setError(await response.text());
        setState("error");
        return;
      }
      setResult((await response.json()) as Record<string, unknown>);
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Housing application analysis failed");
      setState("error");
    }
  }

  async function decide(findingId: string, decision: "confirm" | "dismiss") {
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/housing-application-analyses/findings/${findingId}/decide`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ decision, review_comment: comment || null }),
    });
    if (!response.ok) {
      setError(await response.text());
      setState("error");
      return;
    }
    setResult((await response.json()) as Record<string, unknown>);
  }

  async function markReviewed() {
    if (!result?.id) return;
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/housing-application-analyses/${String(result.id)}/review`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ review_comment: comment || null }),
    });
    if (!response.ok) {
      setError(await response.text());
      setState("error");
      return;
    }
    setResult((await response.json()) as Record<string, unknown>);
  }

  const findings = (result?.findings as Array<Record<string, unknown>> | undefined) ?? [];
  const summary = (result?.checklist_summary as Record<string, number> | undefined) ?? {};

  return (
    <section className={analysisLayoutClass()}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-forest-900">Application checklist analysis</h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
            disabled={state === "loading"}
            onClick={() => void analyse(false)}
          >
            {state === "loading" ? "Analysing…" : "Analyse application"}
          </button>
          <button
            type="button"
            className="rounded-md border border-slate-400 bg-white px-3 py-2 text-sm disabled:opacity-60"
            disabled={state === "loading"}
            onClick={() => void analyse(true)}
          >
            Regenerate
          </button>
        </div>
      </div>
      <p className="text-sm font-medium text-amber-950">{AI_LIMITATION_NOTICE}</p>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {result ? (
        <div className="space-y-3 text-sm">
          <p>
            Status: {String(result.status)} · Version {String(result.version_number)} · AI: {String(result.ai_status)}
            {result.stale === true ? " · Outdated — regenerate" : ""}
          </p>
          <p>
            Complete {summary.complete ?? 0} · Missing {summary.missing ?? 0} · Incomplete {summary.incomplete ?? 0} ·
            Needs review {summary.needs_review ?? 0}
          </p>
          <p className="whitespace-pre-wrap text-slate-800">{String(result.gap_narrative ?? "")}</p>
          {canReview ? (
            <div className="space-y-2">
              <label className="block text-xs" htmlFor="housing-analysis-comment">
                Review comment
              </label>
              <textarea
                id="housing-analysis-comment"
                className="w-full rounded-md border border-slate-300 bg-white p-2"
                maxLength={2000}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
              />
              <button type="button" className="rounded-md border border-slate-400 bg-white px-3 py-2" onClick={() => void markReviewed()}>
                Mark analysis reviewed
              </button>
            </div>
          ) : null}
          <ul className="space-y-2">
            {findings.map((item) => (
              <li key={String(item.id)} className="border-l-2 border-amber-400 pl-3">
                <div className="text-xs uppercase text-slate-600">
                  {findingLabel(String(item.source))} · {outcomeLabel(String(item.outcome))} · {String(item.review_status)}
                </div>
                <div className="font-medium">{String(item.title)}</div>
                <p>{String(item.detail)}</p>
                {item.recommended_action ? <p className="text-slate-600">Next: {String(item.recommended_action)}</p> : null}
                {canReview && item.review_status === "pending" ? (
                  <div className="mt-1 flex gap-2">
                    <button type="button" className="underline" onClick={() => void decide(String(item.id), "confirm")}>
                      Confirm
                    </button>
                    <button type="button" className="underline" onClick={() => void decide(String(item.id), "dismiss")}>
                      Dismiss
                    </button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
