"use client";

import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui/primitives";
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
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        setMessage(null);
        const form = new FormData(event.currentTarget);
        try {
          await createCaseAssignment({
            accessToken,
            organisationId,
            role,
            body: {
              tenant_id: String(form.get("tenant_id") || ""),
              support_worker_user_id: String(form.get("support_worker_user_id") || ""),
              assignment_notes: String(form.get("assignment_notes") || "") || undefined,
            },
          });
          setMessage("Assignment saved. The support worker can now see this case in their caseload.");
          event.currentTarget.reset();
        } catch (err) {
          setError(err instanceof Error ? err.message : "We couldn't save this assignment. Please try again.");
        } finally {
          setPending(false);
        }
      }}
    >
      <div>
        <h2 className="text-base font-semibold text-slate-900">Assign a support worker</h2>
        <p className="mt-0.5 text-sm text-slate-500">Both references are shown on the tenant and team member profiles.</p>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="assignment-tenant" className={labelClass}>
          Tenant reference
        </label>
        <input id="assignment-tenant" name="tenant_id" required className={`${inputClass} font-mono`} />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="assignment-worker" className={labelClass}>
          Support worker reference
        </label>
        <input id="assignment-worker" name="support_worker_user_id" required className={`${inputClass} font-mono`} />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="assignment-notes" className={labelClass}>
          Notes <span className="font-normal text-slate-500">(optional)</span>
        </label>
        <textarea
          id="assignment-notes"
          name="assignment_notes"
          rows={3}
          className={`${inputClass} h-auto py-2`}
          placeholder="Anything the support worker should know before their first visit"
        />
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {message}
        </p>
      ) : null}
      <div className="flex justify-end border-t border-slate-100 pt-4">
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Assign tenant"}
        </button>
      </div>
    </form>
  );
}
