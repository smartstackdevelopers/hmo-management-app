"use client";

import { useState } from "react";
import {
  canApplySupportPlanDraft,
  canReviewSupportPlanDraft,
  draftLayoutClass,
  originLabel,
  visibleGaps,
  type DraftContent,
} from "@/lib/supportPlanDraftView";

type Props = {
  tenantId: string;
  planId?: string | null;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  permissions: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function SupportPlanDraftPanel(props: Props) {
  const [state, setState] = useState<"idle" | "loading" | "error" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [comment, setComment] = useState("");
  const canReview = canReviewSupportPlanDraft(props.permissions);
  const canRun = props.permissions.includes("ai.support_plan_draft.run");

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${props.accessToken}`,
      "Content-Type": "application/json",
      "X-Organisation-Id": props.organisationId,
      ...(props.role ? { "X-HMore-Role": props.role } : {}),
    };
  }

  async function send(path: string, body: unknown) {
    setError(null);
    setState("loading");
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        setError(await response.text());
        setState("error");
        return;
      }
      setResult((await response.json()) as Record<string, unknown>);
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Support plan draft failed");
      setState("error");
    }
  }

  const content = (result?.content as DraftContent | undefined) ?? {};
  const status = typeof result?.status === "string" ? result.status : undefined;
  const stale = result?.stale === true;
  const gaps = visibleGaps(content.gaps);
  const canApply = canApplySupportPlanDraft(props.permissions, status);

  return (
    <section className={draftLayoutClass()}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-forest-900">Support plan draft</h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
            disabled={state === "loading"}
            onClick={() =>
              void send("/api/v1/support-plan-drafts", {
                tenant_id: props.tenantId,
                plan_id: props.planId ?? null,
                force: false,
              })
            }
          >
            {state === "loading" ? "Preparing draft…" : "Generate draft"}
          </button>
          <button
            type="button"
            className="rounded-md border border-slate-400 bg-white px-3 py-2 text-sm disabled:opacity-60"
            disabled={state === "loading"}
            onClick={() =>
              void send("/api/v1/support-plan-drafts", {
                tenant_id: props.tenantId,
                plan_id: props.planId ?? null,
                force: true,
              })
            }
          >
            Regenerate
          </button>
        </div>
      </div>
      <p className="text-sm text-slate-700">
        This panel shows a draft for staff review. It is not the approved support plan, and generating it does not change the plan.
      </p>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {result ? (
        <div className="space-y-3 text-sm">
          <p className="font-medium text-amber-950">{originLabel(String(result.content_origin))}</p>
          <p>
            Status: {String(result.status)} · Version {String(result.version_number)} · Generated{" "}
            {String(result.generated_at ?? "")}
          </p>
          {stale ? (
            <p className="text-red-700" role="alert">
              Source records changed after this draft. Regenerate it before applying.
            </p>
          ) : null}
          <p>{content.situation}</p>
          {gaps.length > 0 ? (
            <div>
              <h3 className="font-medium">Missing information</h3>
              <ul className="list-disc pl-5">
                {gaps.map((gap) => (
                  <li key={gap}>{gap}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div>
            <h3 className="font-medium">Suggested goals</h3>
            <ul className="space-y-2">
              {(content.suggested_goals ?? []).map((goal) => (
                <li key={goal.title} className="border-l-2 border-amber-400 pl-3">
                  <div className="font-medium">{goal.title}</div>
                  <p>{goal.description}</p>
                  {(goal.source_refs ?? []).map((ref) => (
                    <p key={`${ref.type}-${ref.id}`} className="text-xs text-slate-600">
                      Source {ref.type} {ref.id}
                    </p>
                  ))}
                </li>
              ))}
            </ul>
          </div>
          {canRun && status === "draft" ? (
            <button type="button" className="underline" onClick={() => void send(`/api/v1/support-plan-drafts/${String(result.id)}/submit`, {})}>
              Submit for review
            </button>
          ) : null}
          {canReview && status === "pending_review" ? (
            <div className="space-y-2">
              <label className="block text-xs" htmlFor="support-draft-comment">
                Review comment
              </label>
              <textarea
                id="support-draft-comment"
                className="w-full rounded-md border border-slate-300 bg-white p-2"
                maxLength={2000}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
              />
              <div className="flex gap-3">
                <button
                  type="button"
                  className="underline"
                  onClick={() => void send(`/api/v1/support-plan-drafts/${String(result.id)}/approve`, { review_comment: comment || null })}
                >
                  Approve draft
                </button>
                <button
                  type="button"
                  className="underline"
                  onClick={() => void send(`/api/v1/support-plan-drafts/${String(result.id)}/reject`, { review_comment: comment || null })}
                >
                  Reject draft
                </button>
              </div>
            </div>
          ) : null}
          {canApply && result.id ? (
            <button
              type="button"
              className="rounded-md border border-slate-400 bg-white px-3 py-2"
              onClick={() => void send(`/api/v1/support-plan-drafts/${String(result.id)}/apply`, {})}
            >
              Apply approved draft
            </button>
          ) : null}
          {status === "applied" ? <p>Applied to the existing support plan. The plan status was not changed.</p> : null}
        </div>
      ) : null}
    </section>
  );
}
