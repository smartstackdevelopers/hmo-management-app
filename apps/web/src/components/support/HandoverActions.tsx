"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary } from "@/components/ui/primitives";
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
      setError(err instanceof Error ? err.message : "We couldn't update this handover. Please try again.");
    } finally {
      setPending(false);
    }
  }

  const primary =
    status === "draft" && isCreator
      ? { action: "submit" as const, label: "Submit" }
      : status === "submitted" && isRecipient
        ? { action: "acknowledge" as const, label: "Acknowledge" }
        : status === "acknowledged" && (isRecipient || isCreator)
          ? { action: "complete" as const, label: "Complete" }
          : null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {primary ? (
        <button type="button" disabled={pending} onClick={() => void run(primary.action)} className={btnPrimary}>
          {pending ? "Saving…" : primary.label}
        </button>
      ) : null}
      {["draft", "submitted", "acknowledged"].includes(status) && isCreator ? (
        <button type="button" disabled={pending} onClick={() => void run("cancel")} className={btnSecondary}>
          Cancel handover
        </button>
      ) : null}
      {error ? (
        <p role="alert" className="w-full rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}
