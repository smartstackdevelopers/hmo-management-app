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
      setError(await response.text());
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
        className="w-full rounded-md border border-slate-300 p-2 text-sm"
        rows={3}
        maxLength={2000}
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={pending}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          onClick={() => void review("approve")}
        >
          Approve summary
        </button>
        <button
          type="button"
          disabled={pending}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
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
