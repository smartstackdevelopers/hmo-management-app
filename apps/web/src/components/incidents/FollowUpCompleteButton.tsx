"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { completeFollowUp } from "@/lib/incidentsApi";

export function FollowUpCompleteButton({
  followUpId,
  status,
  accessToken,
  organisationId,
  role,
}: {
  followUpId: string;
  status: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  if (status === "completed" || status === "cancelled") return null;
  return (
    <div>
      <button
        type="button"
        className="rounded border border-slate-300 px-2 py-1 text-xs"
        onClick={async () => {
          setError(null);
          try {
            await completeFollowUp({
              accessToken,
              organisationId,
              role,
              followUpId,
            });
            router.refresh();
          } catch (err) {
            setError(err instanceof Error ? err.message : "Failed");
          }
        }}
      >
        Complete
      </button>
      {error ? <p className="text-xs text-red-700">{error}</p> : null}
    </div>
  );
}
