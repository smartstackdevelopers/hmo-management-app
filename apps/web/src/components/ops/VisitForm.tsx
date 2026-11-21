"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
import { createVisit } from "@/lib/opsApi";

export function VisitForm({
  accessToken,
  organisationId,
  role,
  defaultStaffUserId,
  defaultTenantId,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  defaultStaffUserId?: string;
  defaultTenantId?: string;
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
          setError(err instanceof Error ? err.message : "We couldn't book this visit. Please try again.");
          setPending(false);
        }
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="visit-tenant" className={labelClass}>
            Tenant reference
          </label>
          <input id="visit-tenant" name="tenant_id" required defaultValue={defaultTenantId} className={`${inputClass} font-mono`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="visit-staff" className={labelClass}>
            Assigned staff reference
          </label>
          <input id="visit-staff" name="assigned_staff_user_id" required defaultValue={defaultStaffUserId} className={`${inputClass} font-mono`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="visit-when" className={labelClass}>
            When
          </label>
          <input id="visit-when" name="scheduled_at" type="datetime-local" required className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="visit-type" className={labelClass}>
            Visit type
          </label>
          <input id="visit-type" name="visit_type" defaultValue="support" className={inputClass} />
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="visit-purpose" className={labelClass}>
          Purpose
        </label>
        <input id="visit-purpose" name="purpose" required maxLength={255} className={inputClass} />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="visit-location" className={labelClass}>
          Location
        </label>
        <input id="visit-location" name="location" className={inputClass} />
      </div>
      <input type="hidden" name="timezone" value="Europe/London" />
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href="/dashboard/visits" className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Book visit"}
        </button>
      </div>
    </form>
  );
}
