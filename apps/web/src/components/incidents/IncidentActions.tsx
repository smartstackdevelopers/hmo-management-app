"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap gap-2">
        {status === "draft" ? (
          <button
            type="button"
            disabled={pending}
            className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white"
            onClick={() =>
              void run(() =>
                submitIncident({ accessToken, organisationId, role, incidentId }),
              )
            }
          >
            Submit
          </button>
        ) : null}
        {canManage && status === "submitted" ? (
          <button
            type="button"
            disabled={pending}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm"
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
          className="space-y-2 border-t border-slate-100 pt-3"
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
                  due_at: form.get("due_at")
                    ? new Date(String(form.get("due_at"))).toISOString()
                    : null,
                },
              }),
            );
            event.currentTarget.reset();
          }}
        >
          <p className="text-sm font-medium text-forest-900">Add follow-up</p>
          <input
            name="description"
            required
            placeholder="Action description"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <input
            name="assigned_user_id"
            required
            placeholder="Assigned staff user ID"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <input name="due_at" type="datetime-local" className="w-full rounded border px-3 py-2 text-sm" />
          <select name="priority" defaultValue="normal" className="w-full rounded border px-3 py-2 text-sm">
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
          <button type="submit" disabled={pending} className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white">
            Create follow-up
          </button>
        </form>
      ) : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
