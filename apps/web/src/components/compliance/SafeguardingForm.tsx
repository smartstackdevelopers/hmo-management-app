"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
import { createSafeguardingReminder } from "@/lib/complianceApi";

export function SafeguardingForm({
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
          await createSafeguardingReminder({
            accessToken,
            organisationId,
            role,
            body: {
              title: String(form.get("title") || ""),
              category: String(form.get("category") || "follow_up"),
              description: String(form.get("description") || "") || null,
              due_at: new Date(String(form.get("due_at") || "")).toISOString(),
              priority: String(form.get("priority") || "normal"),
              assigned_user_id: String(form.get("assigned_user_id") || ""),
              tenant_id: String(form.get("tenant_id") || "") || null,
            },
          });
          router.push("/dashboard/safeguarding");
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "We couldn't create this reminder. Please try again.");
        } finally {
          setPending(false);
        }
      }}
    >
      <p className="rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-sm text-amber-900">
        Do not put confidential case detail in the title or description. Open the protected record for that.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5 sm:col-span-2">
          <label htmlFor="sg-title" className={labelClass}>
            Title
          </label>
          <input id="sg-title" name="title" required className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="sg-category" className={labelClass}>
            Category
          </label>
          <input id="sg-category" name="category" defaultValue="follow_up" className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="sg-priority" className={labelClass}>
            Priority
          </label>
          <select id="sg-priority" name="priority" defaultValue="normal" className={inputClass}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="sg-staff" className={labelClass}>
            Assigned staff reference
          </label>
          <input id="sg-staff" name="assigned_user_id" required className={`${inputClass} font-mono`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="sg-due" className={labelClass}>
            Due
          </label>
          <input id="sg-due" name="due_at" type="datetime-local" required className={inputClass} />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <label htmlFor="sg-tenant" className={labelClass}>
            Tenant reference
          </label>
          <input id="sg-tenant" name="tenant_id" className={`${inputClass} font-mono`} />
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="sg-description" className={labelClass}>
          Description
        </label>
        <textarea id="sg-description" name="description" rows={3} className={`${inputClass} h-auto py-2`} />
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href="/dashboard/safeguarding" className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Create reminder"}
        </button>
      </div>
    </form>
  );
}
