"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  deactivateCommunityService,
  flagOutdatedCommunityService,
  verifyCommunityService,
} from "@/lib/communityDirectoryApi";

export function CommunityServiceActions({
  accessToken,
  organisationId,
  role,
  serviceId,
  status,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
  status: string;
}) {
  const router = useRouter();
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function run(action: "verify" | "outdated" | "deactivate") {
    setPending(true);
    setError(null);
    try {
      if (action === "verify") {
        await verifyCommunityService({
          accessToken,
          organisationId,
          role,
          serviceId,
          notes: notes || null,
          publish: true,
        });
      } else if (action === "outdated") {
        await flagOutdatedCommunityService({
          accessToken,
          organisationId,
          role,
          serviceId,
          notes: notes || null,
        });
      } else {
        await deactivateCommunityService({
          accessToken,
          organisationId,
          role,
          serviceId,
          notes: notes || null,
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
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-forest-900">Verification actions</h2>
      <p className="text-sm text-slate-600">Current status: {status.replaceAll("_", " ")}</p>
      <label className="block text-sm">
        Internal notes (not shown to tenants)
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
          rows={2}
        />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={pending || status === "inactive"}
          onClick={() => run("verify")}
          className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
        >
          Verify listing
        </button>
        <button
          type="button"
          disabled={pending}
          onClick={() => run("outdated")}
          className="rounded-md border border-amber-600 px-3 py-2 text-sm text-amber-800 disabled:opacity-60"
        >
          Flag outdated
        </button>
        <button
          type="button"
          disabled={pending || status === "inactive"}
          onClick={() => run("deactivate")}
          className="rounded-md border border-red-600 px-3 py-2 text-sm text-red-700 disabled:opacity-60"
        >
          Deactivate
        </button>
      </div>
    </div>
  );
}
