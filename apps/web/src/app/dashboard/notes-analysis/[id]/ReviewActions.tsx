"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

type Props = {
  analysisId: string;
  suggestionId: string;
  canReview: boolean;
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function SuggestionActions(props: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  if (!props.canReview) return null;

  async function decide(decision: "approve" | "reject" | "dismiss") {
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/notes-analysis/suggestions/${props.suggestionId}/decide`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${props.accessToken}`,
        "Content-Type": "application/json",
        "X-Organisation-Id": props.organisationId,
        ...(props.role ? { "X-HMore-Role": props.role } : {}),
      },
      body: JSON.stringify({ decision }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    startTransition(() => router.refresh());
  }

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      <button
        type="button"
        disabled={pending}
        className="border border-slate-300 px-3 py-1 text-sm"
        onClick={() => void decide("approve")}
      >
        Approve suggestion
      </button>
      <button
        type="button"
        disabled={pending}
        className="border border-slate-300 px-3 py-1 text-sm"
        onClick={() => void decide("reject")}
      >
        Reject
      </button>
      <button
        type="button"
        disabled={pending}
        className="border border-slate-300 px-3 py-1 text-sm"
        onClick={() => void decide("dismiss")}
      >
        Dismiss
      </button>
      {error ? <p className="w-full text-sm text-red-700">{error}</p> : null}
    </div>
  );
}

export function AnalysisReviewActions(props: {
  analysisId: string;
  canReview: boolean;
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  if (!props.canReview) return null;

  async function review(decision: "approve" | "partially_approve" | "reject") {
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/notes-analysis/analyses/${props.analysisId}/review`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${props.accessToken}`,
        "Content-Type": "application/json",
        "X-Organisation-Id": props.organisationId,
        ...(props.role ? { "X-HMore-Role": props.role } : {}),
      },
      body: JSON.stringify({ decision }),
    });
    if (!response.ok) {
      setError(await response.text());
      return;
    }
    startTransition(() => router.refresh());
  }

  return (
    <div className="flex flex-wrap gap-2">
      <button type="button" disabled={pending} className="border border-slate-300 px-3 py-1 text-sm" onClick={() => void review("approve")}>
        Mark analysis approved
      </button>
      <button
        type="button"
        disabled={pending}
        className="border border-slate-300 px-3 py-1 text-sm"
        onClick={() => void review("partially_approve")}
      >
        Partially approved
      </button>
      <button type="button" disabled={pending} className="border border-slate-300 px-3 py-1 text-sm" onClick={() => void review("reject")}>
        Reject analysis
      </button>
      {error ? <p className="w-full text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
