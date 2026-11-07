"use client";

import { useState } from "react";
import {
  canReviewDocumentCheck,
  checkLayoutClass,
  findingLabel,
  observationLabel,
} from "@/lib/documentCheckView";

type Props = {
  documentId: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function DocumentCheckPanel(props: Props) {
  const [state, setState] = useState<"idle" | "loading" | "error" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [comment, setComment] = useState("");
  const canReview = canReviewDocumentCheck(props.permissions);

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  async function run(force: boolean) {
    setError(null);
    setState("loading");
    try {
      const response = await fetch(`${API_BASE}/api/v1/document-checks`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ document_id: props.documentId, force }),
      });
      if (!response.ok) {
        setError(await response.text());
        setState("error");
        return;
      }
      setResult((await response.json()) as Record<string, unknown>);
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Document check failed");
      setState("error");
    }
  }

  async function decide(findingId: string, decision: "confirm" | "dismiss") {
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/document-checks/findings/${findingId}/decide`, {
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
    const response = await fetch(`${API_BASE}/api/v1/document-checks/${String(result.id)}/review`, {
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
  const observations = (result?.observations as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <section className={checkLayoutClass()}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-forest-900">Document check</h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
            disabled={state === "loading"}
            onClick={() => void run(false)}
          >
            {state === "loading" ? "Checking…" : "Check document"}
          </button>
          <button
            type="button"
            className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:opacity-60"
            disabled={state === "loading"}
            onClick={() => void run(true)}
          >
            Reprocess
          </button>
        </div>
      </div>
      <p className="text-sm text-slate-600">
        Rules and extraction run first. AI notes, when present, are not verified facts and do not approve the document.
      </p>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {result ? (
        <div className="space-y-3 text-sm">
          <p>
            Status: {String(result.status)} · Extraction: {String(result.extraction_status)} · AI:{" "}
            {String(result.ai_status)} · Checker {String(result.checker_version)} · Document version{" "}
            {String(result.document_version_id)}
          </p>
          {canReview ? (
            <div className="space-y-2">
              <label className="block text-xs text-slate-600" htmlFor="document-check-comment">
                Review comment
              </label>
              <textarea
                id="document-check-comment"
                className="w-full rounded-md border border-slate-300 p-2 text-sm"
                maxLength={2000}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
              />
              <button type="button" className="rounded-md border border-slate-300 px-3 py-2 text-sm" onClick={() => void markReviewed()}>
                Mark reviewed
              </button>
            </div>
          ) : null}
          <p className="text-slate-600">{String(result.summary ?? "")}</p>
          <ul className="space-y-2">
            {findings.map((item) => (
              <li key={String(item.id)} className="border-l-2 border-slate-300 pl-3">
                <div className="text-xs uppercase text-slate-500">
                  {findingLabel(String(item.source))} · {String(item.outcome)} · {String(item.review_status)}
                  {item.page_number ? ` · page ${String(item.page_number)}` : ""}
                </div>
                <div className="font-medium">{String(item.title)}</div>
                <p className="text-slate-700">{String(item.detail)}</p>
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
          {observations.length > 0 ? (
            <div className="space-y-2">
              <h3 className="font-medium">Observations</h3>
              {observations.map((item) => (
                <p key={String(item.id)} className="border border-amber-200 bg-amber-50 p-2">
                  <span className="block text-xs uppercase text-amber-900">
                    {observationLabel(String(item.origin), Boolean(item.ai_generated))}
                  </span>
                  {String(item.body)}
                </p>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}