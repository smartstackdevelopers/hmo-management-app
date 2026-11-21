"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, humanize, inputClass, labelClass } from "@/components/ui/primitives";
import { createDailyLog } from "@/lib/supportApi";

const CATEGORIES = [
  "welfare_check",
  "keywork",
  "housing",
  "health",
  "safeguarding",
  "appointment",
  "phone_call",
  "email",
  "other",
];

const INTERACTIONS = ["in_person", "phone", "video", "message", "collateral", "other"];

function localDateInput(date = new Date()): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function Hint({ children }: { children: string }) {
  return <p className="text-xs leading-5 text-slate-500">{children}</p>;
}

export function DailyLogForm({
  accessToken,
  organisationId,
  role,
  defaultTenantId,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  defaultTenantId?: string;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <form
      className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        try {
          const log = await createDailyLog({
            accessToken,
            organisationId,
            role,
            body: {
              tenant_id: String(form.get("tenant_id") || ""),
              log_date: String(form.get("log_date") || "") || null,
              activity_category: String(form.get("activity_category") || ""),
              summary: String(form.get("summary") || ""),
              notes: String(form.get("notes") || ""),
              interaction_type: String(form.get("interaction_type") || "") || null,
              follow_up_required: form.get("follow_up_required") === "on",
              next_action: String(form.get("next_action") || "") || null,
            },
          });
          router.push(`/dashboard/caseload/${log.tenant_id}`);
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "We couldn't save this log. Please try again.");
          setPending(false);
        }
      }}
    >
      <div>
        <h2 className="text-base font-semibold text-slate-900">Visit details</h2>
        <p className="mt-0.5 text-sm text-slate-500">Record facts clearly. Tenants may request to see their records.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="log-tenant" className={labelClass}>
            Tenant
          </label>
          <input id="log-tenant" name="tenant_id" required defaultValue={defaultTenantId} className={`${inputClass} font-mono`} />
          <Hint>Tenant reference for this log. Names are not stored on the log itself.</Hint>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="log-interaction" className={labelClass}>
            Contact type
          </label>
          <select id="log-interaction" name="interaction_type" className={inputClass} defaultValue="in_person">
            <option value="">Not recorded</option>
            {INTERACTIONS.map((item) => (
              <option key={item} value={item}>
                {humanize(item)}
              </option>
            ))}
          </select>
          <Hint>How you made contact.</Hint>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="log-date" className={labelClass}>
            Date
          </label>
          <input id="log-date" name="log_date" type="date" defaultValue={localDateInput()} className={inputClass} />
          <Hint>The day the contact happened. Today is filled in; change it if you are writing this up later.</Hint>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="log-category" className={labelClass}>
            Activity
          </label>
          <select id="log-category" name="activity_category" required className={inputClass} defaultValue="keywork">
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {humanize(category)}
              </option>
            ))}
          </select>
          <Hint>What the contact was about.</Hint>
        </div>
      </div>
      <div className="space-y-4 border-t border-slate-100 pt-5">
        <h2 className="text-base font-semibold text-slate-900">Notes</h2>
        <div className="space-y-1.5">
          <label htmlFor="log-summary" className={labelClass}>
            Summary
          </label>
          <input id="log-summary" name="summary" required maxLength={255} className={inputClass} />
          <Hint>One line a colleague can scan.</Hint>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="log-notes" className={labelClass}>
            What happened
          </label>
          <textarea id="log-notes" name="notes" required rows={6} className={`${inputClass} h-auto py-2`} />
          <Hint>Write facts, not opinions.</Hint>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 sm:items-start">
          <label htmlFor="log-follow" className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 px-3 py-3">
            <span>
              <span className="block text-sm font-semibold text-slate-900">Follow-up needed</span>
              <span className="mt-0.5 block text-xs text-slate-500">Turn on when someone needs to act after this log.</span>
            </span>
            <span className="relative inline-flex h-6 w-11 shrink-0">
              <input id="log-follow" name="follow_up_required" type="checkbox" className="peer sr-only" />
              <span className="absolute inset-0 rounded-full bg-slate-200 transition peer-checked:bg-brand-700 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-600" />
              <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition peer-checked:translate-x-5" />
            </span>
          </label>
          <div className="space-y-1.5">
            <label htmlFor="log-next" className={labelClass}>
              Next action
            </label>
            <textarea id="log-next" name="next_action" rows={2} className={`${inputClass} h-auto py-2`} />
            <Hint>Optional. What should happen next.</Hint>
          </div>
        </div>
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href={defaultTenantId ? `/dashboard/caseload/${defaultTenantId}` : "/dashboard/support-worker"} className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Save log"}
        </button>
      </div>
    </form>
  );
}
