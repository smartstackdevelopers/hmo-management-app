"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createTraining } from "@/lib/complianceApi";

export function TrainingForm({
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
        const status = String(form.get("status") || "not_started");
        const completion = String(form.get("completion_date") || "");
        const expiry = String(form.get("expiry_date") || "");
        try {
          await createTraining({
            accessToken,
            organisationId,
            role,
            body: {
              staff_user_id: String(form.get("staff_user_id") || ""),
              title: String(form.get("title") || ""),
              category: String(form.get("category") || "general"),
              provider: String(form.get("provider") || "") || null,
              status,
              completion_date: completion || null,
              expiry_date: expiry || null,
              notes: String(form.get("notes") || "") || null,
            },
          });
          router.push("/dashboard/training");
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to create training record");
        } finally {
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        Staff user ID
        <input name="staff_user_id" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Title
        <input name="title" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Category
        <input name="category" defaultValue="general" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Provider
        <input name="provider" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Status
        <select name="status" defaultValue="completed" className="mt-1 w-full rounded border px-3 py-2">
          <option value="not_started">Not started</option>
          <option value="in_progress">In progress</option>
          <option value="completed">Completed</option>
          <option value="exempt">Exempt</option>
        </select>
      </label>
      <label className="block text-sm">
        Completion date
        <input name="completion_date" type="date" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Expiry date
        <input name="expiry_date" type="date" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Notes
        <textarea name="notes" rows={3} className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
      >
        {pending ? "Saving…" : "Save training record"}
      </button>
    </form>
  );
}
