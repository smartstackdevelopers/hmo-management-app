"use client";

import { useState } from "react";
import {
  AI_LIMITATION_NOTICE,
  analysisLayoutClass,
  canReviewComplianceFindings,
  resultLabel,
  reviewLabel,
} from "@/lib/complianceAgentView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function ComplianceAgentPanel(props: Props) {
  const [state, setState] = useState<"idle" | "loading" | "error" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [sweep, setSweep] = useState<Record<string, unknown> | null>(null);
  const [comment, setComment] = useState("");
  const canReview = canReviewComplianceFindings(props.permissions);

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  async function startSweep() {
    setError(null);
    setState("loading");
    try {
      const response = await fetch(`${API_BASE}/api/v1/compliance-agent/sweeps`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({}),
      });
      if (!response.ok) {
        setError(await response.text());
        setState("error");
        return;
      }
      setSweep((await response.json()) as Record<string, unknown>);
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compliance sweep failed");
      setState("error");
    }
  }

  async function review(findingId: string, decision: "confirm" | "dismiss" | "investigate") {
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/compliance-agent/findings/${findingId}/review`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ decision, review_comment: comment || null }),
    });
    if (!response.ok) {
      setError(await response.text());
      setState("error");
      return;
    }
    const updated = (await response.json()) as Record<string, unknown>;
    setSweep((prev) => {
      if (!prev) return prev;
      const findings = ((prev.findings as Array<Record<string, unknown>>) ?? []).map((item) =>
        String(item.id) === String(updated.id) ? updated : item,
      );
      return { ...prev, findings };
    });
  }

  async function resolve(findingId: string) {
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/compliance-agent/findings/${findingId}/resolve`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ review_comment: comment || null }),
    });
    if (!response.ok) {
      setError(await response.text());
      setState("error");
      return;
    }
    const updated = (await response.json()) as Record<string, unknown>;
    setSweep((prev) => {
      if (!prev) return prev;
      const findings = ((prev.findings as Array<Record<string, unknown>>) ?? []).map((item) =>
        String(item.id) === String(updated.id) ? updated : item,
      );
      return { ...prev, findings };
    });
  }

  const findings = (sweep?.findings as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <section className={analysisLayoutClass()}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-forest-900">Compliance rules sweep</h2>
        <button
          type="button"
          className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
          disabled={state === "loading"}
          onClick={() => void startSweep()}
        >
          {state === "loading" ? "Running sweep…" : "Start compliance sweep"}
        </button>
      </div>
      <p className="text-sm font-medium text-amber-950">{AI_LIMITATION_NOTICE}</p>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {sweep ? (
        <div className="space-y-3 text-sm">
          <p>
            Status: {String(sweep.status)} · Records evaluated {String(sweep.records_evaluated)} · Findings created{" "}
            {String(sweep.findings_created)} · Deduplicated {String(sweep.findings_deduplicated)} · AI:{" "}
            {String(sweep.ai_status)}
          </p>
          <p>
            Started {String(sweep.started_at ?? "—")}
            {sweep.completed_at ? ` · Completed ${String(sweep.completed_at)}` : ""}
          </p>
          <div>
            <div className="text-xs uppercase text-slate-600">AI-generated explanation</div>
            <p className="whitespace-pre-wrap text-slate-800">{String(sweep.ai_explanation ?? "")}</p>
          </div>
          {canReview ? (
            <div className="space-y-2">
              <label className="block text-xs" htmlFor="compliance-review-comment">
                Review comment
              </label>
              <textarea
                id="compliance-review-comment"
                className="w-full rounded-md border border-slate-300 bg-white p-2"
                maxLength={2000}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
              />
            </div>
          ) : null}
          <ul className="space-y-2">
            {findings.map((item) => (
              <li key={String(item.id)} className="border-l-2 border-amber-400 pl-3">
                <div className="text-xs uppercase text-slate-600">
                  Rule-confirmed · {resultLabel(String(item.result))} · {reviewLabel(String(item.review_status))} ·{" "}
                  {String(item.resolution_status)}
                </div>
                <div className="font-medium">{String(item.title)}</div>
                <p>{String(item.detail)}</p>
                <p className="text-slate-600">
                  Rule {String(item.rule_id)} v{String(item.rule_version)} · Source {String(item.rule_source)} · Module{" "}
                  {String(item.module)}
                </p>
                {item.ai_explanation ? (
                  <p className="text-slate-700">
                    <span className="text-xs uppercase text-slate-500">AI explanation · </span>
                    {String(item.ai_explanation)}
                  </p>
                ) : null}
                {canReview && item.resolution_status === "open" ? (
                  <div className="mt-1 flex flex-wrap gap-2">
                    <button type="button" className="underline" onClick={() => void review(String(item.id), "confirm")}>
                      Confirm
                    </button>
                    <button
                      type="button"
                      className="underline"
                      onClick={() => void review(String(item.id), "investigate")}
                    >
                      Investigate
                    </button>
                    <button type="button" className="underline" onClick={() => void review(String(item.id), "dismiss")}>
                      Dismiss
                    </button>
                    <button type="button" className="underline" onClick={() => void resolve(String(item.id))}>
                      Mark resolved
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
