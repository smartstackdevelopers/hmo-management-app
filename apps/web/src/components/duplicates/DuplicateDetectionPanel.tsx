"use client";

import { useState } from "react";
import {
  DUPLICATE_DETECTION_NOTICE,
  analysisLayoutClass,
  canReviewDuplicateFindings,
  matchStrengthLabel,
  reviewStatusLabel,
} from "@/lib/duplicateDetectionView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function DuplicateDetectionPanel(props: Props) {
  const [state, setState] = useState<"idle" | "loading" | "error" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<Record<string, unknown> | null>(null);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [comment, setComment] = useState("");
  const canReview = canReviewDuplicateFindings(props.permissions);

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  async function startRun() {
    setError(null);
    setSelected(null);
    setState("loading");
    try {
      const response = await fetch(`${API_BASE}/api/v1/duplicate-detections/runs`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({}),
      });
      if (!response.ok) {
        setError(await response.text());
        setState("error");
        return;
      }
      setRun((await response.json()) as Record<string, unknown>);
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Duplicate detection failed");
      setState("error");
    }
  }

  async function openFinding(findingId: string) {
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/duplicate-detections/findings/${findingId}`, {
      headers: headers(),
    });
    if (!response.ok) {
      setError(await response.text());
      setState("error");
      return;
    }
    setSelected((await response.json()) as Record<string, unknown>);
  }

  async function review(findingId: string, decision: "confirm" | "dismiss" | "defer") {
    setError(null);
    const response = await fetch(
      `${API_BASE}/api/v1/duplicate-detections/findings/${findingId}/review`,
      {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ decision, review_comment: comment || null }),
      },
    );
    if (!response.ok) {
      setError(await response.text());
      setState("error");
      return;
    }
    const updated = (await response.json()) as Record<string, unknown>;
    setSelected(updated);
    setRun((prev) => {
      if (!prev) return prev;
      const findings = ((prev.findings as Array<Record<string, unknown>>) ?? []).map((item) =>
        String(item.id) === String(updated.id) ? updated : item,
      );
      return { ...prev, findings };
    });
  }

  const findings = (run?.findings as Array<Record<string, unknown>> | undefined) ?? [];
  const sourceRecord = selected?.source_record as Record<string, unknown> | undefined;
  const candidateRecord = selected?.candidate_record as Record<string, unknown> | undefined;

  return (
    <section className={analysisLayoutClass()}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-forest-900">Duplicate detection</h2>
        <button
          type="button"
          className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
          disabled={state === "loading"}
          onClick={() => void startRun()}
        >
          {state === "loading" ? "Searching…" : "Run duplicate check"}
        </button>
      </div>
      <p className="text-sm font-medium text-amber-950">{DUPLICATE_DETECTION_NOTICE}</p>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {state === "ready" && findings.length === 0 ? (
        <p className="text-sm text-forest-800">No potential duplicates found in this organisation scope.</p>
      ) : null}
      {run ? (
        <p className="text-xs text-forest-700">
          Scanned {String(run.records_scanned)} · compared {String(run.candidates_compared)} · created{" "}
          {String(run.findings_created)} · AI used: {String(run.used_ai)}
        </p>
      ) : null}
      {findings.length > 0 ? (
        <ul className="space-y-2">
          {findings.map((item) => (
            <li
              key={String(item.id)}
              className="flex flex-wrap items-start justify-between gap-2 border-b border-amber-100 pb-2"
            >
              <div className="space-y-1 text-sm text-forest-900">
                <p className="font-medium">
                  {String(item.record_type)} · {matchStrengthLabel(String(item.match_strength))}
                </p>
                <p className="text-xs text-forest-700">
                  {((item.matching_reasons as string[]) ?? []).join(" · ") || "No reasons listed"}
                </p>
                {item.similarity_score != null ? (
                  <p className="text-xs text-forest-600">
                    Matching strength score: {String(item.similarity_score)} (not identity proof)
                  </p>
                ) : null}
                <p className="text-xs">{reviewStatusLabel(String(item.review_status))}</p>
              </div>
              <button
                type="button"
                className="rounded-md border border-forest-300 px-2 py-1 text-xs"
                onClick={() => void openFinding(String(item.id))}
              >
                Compare
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {selected ? (
        <div className="space-y-3 border-t border-amber-200 pt-3">
          <h3 className="text-base font-semibold text-forest-900">Side-by-side comparison</h3>
          <div className="grid gap-3 md:grid-cols-2">
            <pre className="overflow-auto rounded-md bg-white/70 p-2 text-xs">
              {JSON.stringify(sourceRecord ?? {}, null, 2)}
            </pre>
            <pre className="overflow-auto rounded-md bg-white/70 p-2 text-xs">
              {JSON.stringify(candidateRecord ?? {}, null, 2)}
            </pre>
          </div>
          {canReview ? (
            <div className="space-y-2">
              <label className="block text-sm text-forest-800">
                Review comment
                <textarea
                  className="mt-1 w-full rounded-md border border-forest-200 p-2 text-sm"
                  rows={2}
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-md bg-teal-800 px-3 py-1.5 text-sm text-white"
                  onClick={() => void review(String(selected.id), "confirm")}
                >
                  Confirm duplicate
                </button>
                <button
                  type="button"
                  className="rounded-md border border-forest-400 px-3 py-1.5 text-sm"
                  onClick={() => void review(String(selected.id), "dismiss")}
                >
                  Mark as not duplicate
                </button>
                <button
                  type="button"
                  className="rounded-md border border-forest-300 px-3 py-1.5 text-sm"
                  onClick={() => void review(String(selected.id), "defer")}
                >
                  Defer
                </button>
              </div>
              <p className="text-xs text-forest-700">
                Confirming records a review decision only. Source records are never deleted or merged by
                this action.
              </p>
            </div>
          ) : (
            <p className="text-sm text-forest-700">You do not have permission to review findings.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}
