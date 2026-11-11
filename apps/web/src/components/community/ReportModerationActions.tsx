"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-5"
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
      <h2 className="text-sm font-semibold text-forest-900">Update moderation status</h2>
      <label className="block text-sm">
        Status
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
        >
          {STATUSES.map((value) => (
            <option key={value} value={value}>
              {value.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        Resolution notes
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
          rows={3}
        />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
      >
        {pending ? "Saving…" : "Save moderation"}
      </button>
    </form>
  );
}
