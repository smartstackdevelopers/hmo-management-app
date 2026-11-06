"use client";

import { useState } from "react";
import { createCaseAssignment } from "@/lib/supportApi";

export function AssignmentForm({
  accessToken,
  organisationId,
  role,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <form
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        setMessage(null);
        const form = new FormData(event.currentTarget);
        try {
          const row = await createCaseAssignment({
            accessToken,
            organisationId,
            role,
            body: {
              tenant_id: String(form.get("tenant_id") || ""),
              support_worker_user_id: String(form.get("support_worker_user_id") || ""),
              assignment_notes: String(form.get("assignment_notes") || "") || undefined,
            },
          });
          setMessage(`Assignment ${row.id} created for tenant ${row.tenant_id}.`);
          event.currentTarget.reset();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Assignment failed");
        } finally {
          setPending(false);
        }
      }}
    >
      <h3 className="font-semibold text-forest-900">Assign support worker</h3>
      <label className="block text-sm">
        Tenant ID
        <input name="tenant_id" required className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm" />
      </label>
      <label className="block text-sm">
        Support worker user ID
        <input
          name="support_worker_user_id"
          required
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block text-sm">
        Notes
        <textarea name="assignment_notes" rows={2} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {message ? <p className="text-sm text-teal-800">{message}</p> : null}
      <button type="submit" disabled={pending} className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60">
        {pending ? "Saving…" : "Create assignment"}
      </button>
    </form>
  );
}
