"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
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
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
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
          setError(err instanceof Error ? err.message : "We couldn't create this task. Please try again.");
          setPending(false);
        }
      }}
    >
      <div className="space-y-1.5">
        <label htmlFor="task-title" className={labelClass}>
          Title
        </label>
        <input id="task-title" name="title" required className={inputClass} />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="task-description" className={labelClass}>
          Description
        </label>
        <textarea id="task-description" name="description" rows={3} className={`${inputClass} h-auto py-2`} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="task-assignee" className={labelClass}>
            Assigned staff reference
          </label>
          <input id="task-assignee" name="assigned_user_id" required defaultValue={defaultAssigneeId} className={`${inputClass} font-mono`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="task-tenant" className={labelClass}>
            Tenant reference
          </label>
          <input id="task-tenant" name="tenant_id" className={`${inputClass} font-mono`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="task-priority" className={labelClass}>
            Priority
          </label>
          <select id="task-priority" name="priority" defaultValue="normal" className={inputClass}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="task-due" className={labelClass}>
            Due
          </label>
          <input id="task-due" name="due_at" type="datetime-local" className={inputClass} />
        </div>
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href="/dashboard/tasks" className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Create task"}
        </button>
      </div>
    </form>
  );
}
