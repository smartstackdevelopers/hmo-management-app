"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createShift } from "@/lib/opsApi";

export function ShiftForm({
  accessToken,
  organisationId,
  role,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <form
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        const shiftDate = String(form.get("shift_date") || "");
        const starts = String(form.get("starts_at") || "");
        const ends = String(form.get("ends_at") || "");
        try {
          await createShift({
            accessToken,
            organisationId,
            role,
            body: {
              staff_user_id: String(form.get("staff_user_id") || ""),
              shift_date: shiftDate,
              starts_at: new Date(starts).toISOString(),
              ends_at: new Date(ends).toISOString(),
              timezone: String(form.get("timezone") || "Europe/London"),
              shift_type: String(form.get("shift_type") || "standard"),
              location: String(form.get("location") || "") || null,
              notes: String(form.get("notes") || "") || null,
            },
          });
          router.push("/dashboard/rota");
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to create shift");
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        Staff user ID
        <input name="staff_user_id" required className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm" />
      </label>
      <label className="block text-sm">
        Shift date
        <input name="shift_date" type="date" required className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Starts at
        <input name="starts_at" type="datetime-local" required className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Ends at
        <input name="ends_at" type="datetime-local" required className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Timezone
        <input name="timezone" defaultValue="Europe/London" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Shift type
        <input name="shift_type" defaultValue="standard" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Location
        <input name="location" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Notes
        <textarea name="notes" rows={2} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={pending} className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60">
        {pending ? "Saving…" : "Create shift"}
      </button>
    </form>
  );
}
