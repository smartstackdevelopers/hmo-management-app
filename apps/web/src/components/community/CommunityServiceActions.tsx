"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnDanger, btnSecondary, humanize, inputClass, labelClass, StatusChip } from "@/components/ui/primitives";
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
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-900">Verification</h2>
        <StatusChip status={status} />
      </div>
      <p className="text-sm text-slate-500">Current status: {humanize(status)}. Notes stay internal.</p>
      <div className="space-y-1.5">
        <label htmlFor="verify-notes" className={labelClass}>
          Internal notes
        </label>
        <textarea id="verify-notes" value={notes} onChange={(event) => setNotes(event.target.value)} className={`${inputClass} h-auto py-2`} rows={2} />
      </div>
      {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={pending || status === "inactive"} onClick={() => void run("verify")} className={btnSecondary}>
          Verify listing
        </button>
        <button type="button" disabled={pending} onClick={() => void run("outdated")} className={btnSecondary}>
          Flag outdated
        </button>
        <button type="button" disabled={pending || status === "inactive"} onClick={() => void run("deactivate")} className={btnDanger}>
          Deactivate
        </button>
      </div>
    </div>
  );
}
