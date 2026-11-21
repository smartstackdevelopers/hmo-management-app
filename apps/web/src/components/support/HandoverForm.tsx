"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
import { createHandover } from "@/lib/supportApi";

export function HandoverForm({
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
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        try {
          const handover = await createHandover({
            accessToken,
            organisationId,
            role,
            body: {
              tenant_id: String(form.get("tenant_id") || ""),
              recipient_user_id: String(form.get("recipient_user_id") || ""),
              summary: String(form.get("summary") || ""),
              case_updates: String(form.get("case_updates") || "") || null,
              outstanding_tasks: String(form.get("outstanding_tasks") || "") || null,
              follow_up_actions: String(form.get("follow_up_actions") || "") || null,
              priority: String(form.get("priority") || "normal"),
              submit: form.get("submit") === "on",
            },
          });
          router.push(`/dashboard/handovers/${handover.id}`);
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "We couldn't save this handover. Please try again.");
          setPending(false);
        }
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="handover-tenant" className={labelClass}>
            Tenant reference
          </label>
          <input id="handover-tenant" name="tenant_id" required defaultValue={defaultTenantId} className={`${inputClass} font-mono`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="handover-recipient" className={labelClass}>
            Recipient reference
          </label>
          <input id="handover-recipient" name="recipient_user_id" required className={`${inputClass} font-mono`} />
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="handover-summary" className={labelClass}>
          Summary
        </label>
        <input id="handover-summary" name="summary" required maxLength={255} className={inputClass} />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="handover-updates" className={labelClass}>
          Case updates
        </label>
        <textarea id="handover-updates" name="case_updates" rows={4} className={`${inputClass} h-auto py-2`} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="handover-tasks" className={labelClass}>
            Outstanding tasks
          </label>
          <textarea id="handover-tasks" name="outstanding_tasks" rows={3} className={`${inputClass} h-auto py-2`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="handover-follow" className={labelClass}>
            Follow-up actions
          </label>
          <textarea id="handover-follow" name="follow_up_actions" rows={3} className={`${inputClass} h-auto py-2`} />
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="handover-priority" className={labelClass}>
          Priority
        </label>
        <select id="handover-priority" name="priority" defaultValue="normal" className={inputClass}>
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
      </div>
      <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
        <input type="checkbox" name="submit" className="h-4 w-4 rounded border-slate-300 text-brand-700 focus:ring-brand-600" />
        Submit now (otherwise this stays a draft)
      </label>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href="/dashboard/handovers" className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Save handover"}
        </button>
      </div>
    </form>
  );
}
