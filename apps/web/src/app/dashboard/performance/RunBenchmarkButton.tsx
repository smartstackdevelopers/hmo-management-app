"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { btnPrimary } from "@/components/ui/primitives";
import { runPerformanceBenchmark } from "@/lib/performanceApi";

export function RunBenchmarkButton({
  accessToken,
  organisationId,
  role,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="space-y-2">
      <button
        type="button"
        className={btnPrimary}
        disabled={pending}
        onClick={async () => {
          setPending(true);
          setError(null);
          try {
            await runPerformanceBenchmark({ accessToken, organisationId, role }, 5);
            router.refresh();
          } catch {
            setError("The benchmark could not be started.");
          } finally {
            setPending(false);
          }
        }}
      >
        {pending ? "Running…" : "Run benchmark"}
      </button>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
