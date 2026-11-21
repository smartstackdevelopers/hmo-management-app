"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

type Props = {
  summaryId: string;
  canReview: boolean;
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function SummaryReviewActions(props: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  if (!props.canReview) return null;

  async function review(decision: "approve" | "reject") {
    setError(null);
    const response = await fetch(`${API_BASE}/api/v1/case-summaries/${props.summaryId}/review`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${props.accessToken}`,
        "Content-Type": "application/json",
        "X-Organisation-Id": props.organisationId,
        ...(props.role ? { "X-HMore-Role": props.role } : {}),
      },
      body: JSON.stringify({ decision, review_comment: comment || null }),
    });
    if (!response.ok) {
      setError("We couldn't save that review. Please try again.");
      return;
    }
    startTransition(() => router.refresh());
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm text-slate-700" htmlFor="review-comment">
        Review comment
      </label>
      <textarea
        id="review-comment"
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
        rows={3}
        maxLength={2000}
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={pending}
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          onClick={() => void review("approve")}
        >
          Approve summary
        </button>
        <button
          type="button"
          disabled={pending}
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          onClick={() => void review("reject")}
        >
          Reject summary
        </button>
      </div>
      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
