"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  acknowledgeSafeguardingReminder,
  completeSafeguardingReminder,
} from "@/lib/complianceApi";

export function SafeguardingActions({
  reminderId,
  status,
  accessToken,
  organisationId,
  role,
}: {
  reminderId: string;
  status: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  if (status === "completed" || status === "cancelled") {
    return null;
  }

  async function run(action: "acknowledge" | "complete") {
    setPending(true);
    setError(null);
    try {
      if (action === "acknowledge") {
        await acknowledgeSafeguardingReminder({
          accessToken,
          organisationId,
          role,
          reminderId,
        });
      } else {
        await completeSafeguardingReminder({
          accessToken,
          organisationId,
          role,
          reminderId,
        });
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {status !== "acknowledged" ? (
        <button
          type="button"
          disabled={pending}
          onClick={() => void run("acknowledge")}
          className="rounded border border-slate-300 px-2 py-1 text-xs"
        >
          Acknowledge
        </button>
      ) : null}
      <button
        type="button"
        disabled={pending}
        onClick={() => void run("complete")}
        className="rounded bg-teal-700 px-2 py-1 text-xs text-white"
      >
        Complete
      </button>
      {error ? <p className="w-full text-xs text-red-700">{error}</p> : null}
    </div>
  );
}
