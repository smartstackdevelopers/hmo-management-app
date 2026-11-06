"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { transitionHandover } from "@/lib/supportApi";

export function HandoverActions({
  accessToken,
  organisationId,
  role,
  handoverId,
  status,
  isRecipient,
  isCreator,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  handoverId: string;
  status: string;
  isRecipient: boolean;
  isCreator: boolean;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function run(action: "submit" | "acknowledge" | "complete" | "cancel") {
    setPending(true);
    setError(null);
    try {
      await transitionHandover({
        accessToken,
        organisationId,
        role,
        handoverId,
        action,
      });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {status === "draft" && isCreator ? (
        <button
          type="button"
          disabled={pending}
          onClick={() => run("submit")}
          className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
        >
          Submit
        </button>
      ) : null}
      {status === "submitted" && isRecipient ? (
        <button
          type="button"
          disabled={pending}
          onClick={() => run("acknowledge")}
          className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
        >
          Acknowledge
        </button>
      ) : null}
      {status === "acknowledged" && (isRecipient || isCreator) ? (
        <button
          type="button"
          disabled={pending}
          onClick={() => run("complete")}
          className="rounded-md bg-forest-900 px-3 py-2 text-sm text-white disabled:opacity-60"
        >
          Complete
        </button>
      ) : null}
      {["draft", "submitted", "acknowledged"].includes(status) && isCreator ? (
        <button
          type="button"
          disabled={pending}
          onClick={() => run("cancel")}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:opacity-60"
        >
          Cancel
        </button>
      ) : null}
      {error ? <p className="w-full text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
