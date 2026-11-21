"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, humanize, inputClass, labelClass } from "@/components/ui/primitives";
import { updateAdminReport } from "@/lib/helpNearMeApi";

const STATUSES = [
  "submitted",
  "under_review",
  "information_confirmed",
  "listing_updated",
  "reverified",
  "rejected",
  "closed",
] as const;

export function ReportModerationActions({
  accessToken,
  organisationId,
  role,
  reportId,
  currentStatus,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  reportId: string;
  currentStatus: string;
}) {
  const router = useRouter();
  const [status, setStatus] = useState(currentStatus);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <form
      className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        try {
          await updateAdminReport({
            accessToken,
            organisationId,
            role,
            reportId,
            status,
            resolution_notes: notes || null,
          });
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Moderation update failed");
        } finally {
          setPending(false);
        }
      }}
    >
      <h2 className="text-base font-semibold text-slate-900">Update moderation</h2>
      <div className="space-y-1.5">
        <label htmlFor="report-status" className={labelClass}>
          Status
        </label>
        <select id="report-status" value={status} onChange={(event) => setStatus(event.target.value)} className={inputClass}>
          {STATUSES.map((value) => (
            <option key={value} value={value}>
              {humanize(value)}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="report-notes" className={labelClass}>
          Resolution notes
        </label>
        <textarea id="report-notes" value={notes} onChange={(event) => setNotes(event.target.value)} className={`${inputClass} h-auto py-2`} rows={3} />
      </div>
      {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
      <div className="flex justify-end">
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Save moderation"}
        </button>
      </div>
    </form>
  );
}
