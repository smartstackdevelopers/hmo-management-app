"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
import { createFollowUp, patchIncident, submitIncident } from "@/lib/incidentsApi";

export function IncidentActions({
  incidentId,
  status,
  accessToken,
  organisationId,
  role,
  canManage,
}: {
  incidentId: string;
  status: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function run(action: () => Promise<unknown>) {
    setPending(true);
    setError(null);
    try {
      await action();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't update this incident. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="flex flex-wrap gap-2">
        {status === "draft" ? (
          <button
            type="button"
            disabled={pending}
            className={btnPrimary}
            onClick={() => void run(() => submitIncident({ accessToken, organisationId, role, incidentId }))}
          >
            Submit
          </button>
        ) : null}
        {canManage && status === "submitted" ? (
          <button
            type="button"
            disabled={pending}
            className={btnPrimary}
            onClick={() =>
              void run(() =>
                patchIncident({
                  accessToken,
                  organisationId,
                  role,
                  incidentId,
                  body: { status: "under_review" },
                }),
              )
            }
          >
            Start review
          </button>
        ) : null}
      </div>
      {canManage || status !== "draft" ? (
        <form
          className="space-y-3 border-t border-slate-100 pt-4"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void run(() =>
              createFollowUp({
                accessToken,
                organisationId,
                role,
                incidentId,
                body: {
                  description: String(form.get("description") || ""),
                  assigned_user_id: String(form.get("assigned_user_id") || ""),
                  priority: String(form.get("priority") || "normal"),
                  due_at: form.get("due_at") ? new Date(String(form.get("due_at"))).toISOString() : null,
                },
              }),
            );
            event.currentTarget.reset();
          }}
        >
          <h2 className="text-sm font-semibold text-slate-900">Add follow-up</h2>
          <div className="space-y-1.5">
            <label htmlFor="follow-description" className={labelClass}>
              Action
            </label>
            <input id="follow-description" name="description" required className={inputClass} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="follow-assignee" className={labelClass}>
                Assigned staff reference
              </label>
              <input id="follow-assignee" name="assigned_user_id" required className={`${inputClass} font-mono`} />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="follow-due" className={labelClass}>
                Due
              </label>
              <input id="follow-due" name="due_at" type="datetime-local" className={inputClass} />
            </div>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="follow-priority" className={labelClass}>
              Priority
            </label>
            <select id="follow-priority" name="priority" defaultValue="normal" className={inputClass}>
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
          <div className="flex justify-end">
            <button type="submit" disabled={pending} className={status === "draft" || (canManage && status === "submitted") ? btnSecondary : btnPrimary}>
              Create follow-up
            </button>
          </div>
        </form>
      ) : null}
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}
