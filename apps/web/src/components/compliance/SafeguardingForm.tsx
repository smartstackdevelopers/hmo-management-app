"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        const due = String(form.get("due_at") || "");
        try {
          await createSafeguardingReminder({
            accessToken,
            organisationId,
            role,
            body: {
              title: String(form.get("title") || ""),
              category: String(form.get("category") || "follow_up"),
              description: String(form.get("description") || "") || null,
              due_at: new Date(due).toISOString(),
              priority: String(form.get("priority") || "normal"),
              assigned_user_id: String(form.get("assigned_user_id") || ""),
              tenant_id: String(form.get("tenant_id") || "") || null,
            },
          });
          router.push("/dashboard/safeguarding");
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to create reminder");
        } finally {
          setPending(false);
        }
      }}
    >
      <p className="text-sm text-slate-600">
        Do not put confidential safeguarding case details in the title or description. Open the
        protected application for case content.
      </p>
      <label className="block text-sm">
        Title
        <input name="title" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Category
        <input name="category" defaultValue="follow_up" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Assigned staff user ID
        <input name="assigned_user_id" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Tenant ID (optional)
        <input name="tenant_id" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Due at
        <input name="due_at" type="datetime-local" required className="mt-1 w-full rounded border px-3 py-2" />
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
      <label className="block text-sm">
        Description (non-sensitive)
        <textarea name="description" rows={3} className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
      >
        {pending ? "Saving…" : "Create reminder"}
      </button>
    </form>
  );
}
