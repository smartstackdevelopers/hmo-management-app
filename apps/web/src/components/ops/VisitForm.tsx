"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createVisit } from "@/lib/opsApi";

export function VisitForm({
  accessToken,
  organisationId,
  role,
  defaultStaffUserId,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  defaultStaffUserId?: string;
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
        try {
          await createVisit({
            accessToken,
            organisationId,
            role,
            body: {
              tenant_id: String(form.get("tenant_id") || ""),
              assigned_staff_user_id: String(form.get("assigned_staff_user_id") || ""),
              scheduled_at: new Date(String(form.get("scheduled_at") || "")).toISOString(),
              purpose: String(form.get("purpose") || ""),
              visit_type: String(form.get("visit_type") || "support"),
              location: String(form.get("location") || "") || null,
              timezone: String(form.get("timezone") || "Europe/London"),
            },
          });
          router.push("/dashboard/visits");
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to schedule visit");
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        Tenant ID
        <input name="tenant_id" required className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm" />
      </label>
      <label className="block text-sm">
        Assigned staff user ID
        <input
          name="assigned_staff_user_id"
          required
          defaultValue={defaultStaffUserId}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block text-sm">
        Scheduled at
        <input name="scheduled_at" type="datetime-local" required className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Purpose
        <input name="purpose" required maxLength={255} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Visit type
        <input name="visit_type" defaultValue="support" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Location
        <input name="location" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <input type="hidden" name="timezone" value="Europe/London" />
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={pending} className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60">
        {pending ? "Saving…" : "Schedule visit"}
      </button>
    </form>
  );
}
