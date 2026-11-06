"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-4"
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
      <label className="block text-sm">
        Title
        <input name="title" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Description
        <textarea name="description" required rows={5} className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          Category
          <select name="category_code" defaultValue="general" className="mt-1 w-full rounded border px-3 py-2">
            <option value="general">General</option>
            <option value="housing">Housing</option>
            <option value="support">Support</option>
            <option value="maintenance">Maintenance</option>
            <option value="staff">Staff conduct</option>
          </select>
        </label>
        <label className="block text-sm">
          Priority
          <select name="priority" defaultValue="normal" className="mt-1 w-full rounded border px-3 py-2">
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </label>
      </div>
      <p className="text-xs text-slate-500">
        Categories and priorities are organisation operational settings, not statutory classifications.
      </p>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
      >
        {pending ? "Submitting…" : "Submit complaint"}
      </button>
    </form>
  );
}
