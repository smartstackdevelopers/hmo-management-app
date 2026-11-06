"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-5"
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
          setError(err instanceof Error ? err.message : "Failed to create handover");
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        <span className="font-medium">Tenant ID</span>
        <input
          name="tenant_id"
          required
          defaultValue={defaultTenantId}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block text-sm">
        <span className="font-medium">Recipient support worker user ID</span>
        <input
          name="recipient_user_id"
          required
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block text-sm">
        <span className="font-medium">Summary</span>
        <input name="summary" required maxLength={255} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        <span className="font-medium">Case updates</span>
        <textarea name="case_updates" rows={4} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        <span className="font-medium">Outstanding tasks</span>
        <textarea name="outstanding_tasks" rows={3} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        <span className="font-medium">Follow-up actions</span>
        <textarea name="follow_up_actions" rows={3} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <label className="block text-sm">
        <span className="font-medium">Priority</span>
        <select name="priority" defaultValue="normal" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
          <option value="low">low</option>
          <option value="normal">normal</option>
          <option value="high">high</option>
          <option value="urgent">urgent</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" name="submit" />
        Submit immediately (otherwise save as draft)
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={pending} className="rounded-md bg-teal-700 px-4 py-2 text-sm text-white disabled:opacity-60">
        {pending ? "Saving…" : "Save handover"}
      </button>
    </form>
  );
}
