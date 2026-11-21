"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
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
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        try {
          await createShift({
            accessToken,
            organisationId,
            role,
            body: {
              staff_user_id: String(form.get("staff_user_id") || ""),
              shift_date: String(form.get("shift_date") || ""),
              starts_at: new Date(String(form.get("starts_at") || "")).toISOString(),
              ends_at: new Date(String(form.get("ends_at") || "")).toISOString(),
              timezone: String(form.get("timezone") || "Europe/London"),
              shift_type: String(form.get("shift_type") || "standard"),
              location: String(form.get("location") || "") || null,
              notes: String(form.get("notes") || "") || null,
            },
          });
          router.push("/dashboard/rota");
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "We couldn't add this shift. Please try again.");
          setPending(false);
        }
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5 sm:col-span-2">
          <label htmlFor="shift-staff" className={labelClass}>
            Staff reference
          </label>
          <input id="shift-staff" name="staff_user_id" required className={`${inputClass} font-mono`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="shift-date" className={labelClass}>
            Shift date
          </label>
          <input id="shift-date" name="shift_date" type="date" required className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="shift-type" className={labelClass}>
            Shift type
          </label>
          <input id="shift-type" name="shift_type" defaultValue="standard" className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="shift-start" className={labelClass}>
            Starts
          </label>
          <input id="shift-start" name="starts_at" type="datetime-local" required className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="shift-end" className={labelClass}>
            Ends
          </label>
          <input id="shift-end" name="ends_at" type="datetime-local" required className={inputClass} />
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="shift-timezone" className={labelClass}>
          Timezone
        </label>
        <input id="shift-timezone" name="timezone" defaultValue="Europe/London" className={inputClass} />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="shift-location" className={labelClass}>
          Location
        </label>
        <input id="shift-location" name="location" className={inputClass} />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="shift-notes" className={labelClass}>
          Notes
        </label>
        <textarea id="shift-notes" name="notes" rows={2} className={`${inputClass} h-auto py-2`} />
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href="/dashboard/rota" className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Add shift"}
        </button>
      </div>
    </form>
  );
}
