"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createTask } from "@/lib/opsApi";

export function TaskForm({
  accessToken,
  organisationId,
  role,
  defaultAssigneeId,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  defaultAssigneeId?: string;
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
          await createTask({
            accessToken,
            organisationId,
            role,
            body: {
              title: String(form.get("title") || ""),
              description: String(form.get("description") || "") || null,
              assigned_user_id: String(form.get("assigned_user_id") || ""),
              tenant_id: String(form.get("tenant_id") || "") || null,
              priority: String(form.get("priority") || "normal"),
              due_at: due ? new Date(due).toISOString() : null,
            },
          });
          router.push("/dashboard/tasks");
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to create task");
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        Title
        <input name="title" required className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Description
        <textarea name="description" rows={3} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        Assigned user ID
        <input
          name="assigned_user_id"
          required
          defaultValue={defaultAssigneeId}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block text-sm">
        Tenant ID (optional)
        <input name="tenant_id" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm" />
      </label>
      <label className="block text-sm">
        Priority
        <select name="priority" defaultValue="normal" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
          <option value="low">low</option>
          <option value="normal">normal</option>
          <option value="high">high</option>
          <option value="urgent">urgent</option>
        </select>
      </label>
      <label className="block text-sm">
        Due at
        <input name="due_at" type="datetime-local" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={pending} className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60">
        {pending ? "Saving…" : "Create task"}
      </button>
    </form>
  );
}
