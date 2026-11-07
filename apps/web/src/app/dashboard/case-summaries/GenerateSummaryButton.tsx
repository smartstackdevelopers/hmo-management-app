"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { nextGenState, type GenState } from "@/lib/caseSummaryView";

type Props = {
  tenantId: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  force?: boolean;
  label?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function GenerateSummaryButton(props: Props) {
  const router = useRouter();
  const [state, setState] = useState<GenState>("idle");
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setError(null);
    setState(nextGenState("start"));
    try {
      const response = await fetch(`${API_BASE}/api/v1/case-summaries`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${props.accessToken}`,
          "Content-Type": "application/json",
          "X-Organisation-Id": props.organisationId,
          ...(props.role ? { "X-HMore-Role": props.role } : {}),
        },
        body: JSON.stringify({ tenant_id: props.tenantId, force: props.force ?? false }),
      });
      if (!response.ok) {
        setError(await response.text());
        setState(nextGenState("failure"));
        return;
      }
      const data = (await response.json()) as { id?: string };
      setState(nextGenState("success"));
      if (data.id) {
        router.push(`/dashboard/case-summaries/${data.id}`);
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Case summary request failed");
      setState(nextGenState("failure"));
    }
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => void generate()}
        disabled={state === "loading"}
        className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
      >
        {state === "loading" ? "Generating summary…" : props.label ?? "Generate case summary"}
      </button>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
