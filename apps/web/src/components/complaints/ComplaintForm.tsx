"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui/primitives";
import { createComplaint } from "@/lib/complaintsApi";

export function ComplaintForm({
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
      className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        setPending(true);
        setError(null);
        void createComplaint({
          accessToken,
          organisationId,
          role,
          body: {
            title: String(form.get("title") || ""),
            description: String(form.get("description") || ""),
            category_code: String(form.get("category_code") || "general"),
            priority: String(form.get("priority") || "normal"),
            tenant_id: defaultTenantId || undefined,
          },
        })
          .then((complaint) => router.push(`/dashboard/complaints/${complaint.id}`))
          .catch((err) => setError(err instanceof Error ? err.message : "Submit failed"))
          .finally(() => setPending(false));
      }}
    >
      <div>
        <label htmlFor="complaint-title" className={labelClass}>
          Title
        </label>
        <input id="complaint-title" name="title" required className={`mt-1.5 ${inputClass}`} />
      </div>
      <div>
        <label htmlFor="complaint-description" className={labelClass}>
          Description
        </label>
        <textarea id="complaint-description" name="description" required rows={5} className={`mt-1.5 ${inputClass} h-auto py-2`} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="complaint-category" className={labelClass}>
            Category
          </label>
          <select id="complaint-category" name="category_code" defaultValue="general" className={`mt-1.5 ${inputClass}`}>
            <option value="general">General</option>
            <option value="housing">Housing</option>
            <option value="support">Support</option>
            <option value="maintenance">Maintenance</option>
            <option value="staff">Staff conduct</option>
          </select>
        </div>
        <div>
          <label htmlFor="complaint-priority" className={labelClass}>
            Priority
          </label>
          <select id="complaint-priority" name="priority" defaultValue="normal" className={`mt-1.5 ${inputClass}`}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
      </div>
      <p className="text-xs text-slate-500">
        Categories and priorities are organisation operational settings, not statutory classifications.
      </p>
      {error ? (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end border-t border-slate-100 pt-5">
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Submitting…" : "Submit complaint"}
        </button>
      </div>
    </form>
  );
}
