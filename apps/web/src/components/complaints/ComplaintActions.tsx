"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  addComplaintNote,
  assignComplaint,
  changeComplaintPriority,
  escalateComplaint,
  transitionComplaint,
  updateComplaintDeadlines,
} from "@/lib/complaintsApi";

export function ComplaintActions({
  complaintId,
  status,
  accessToken,
  organisationId,
  role,
  canManage,
  canAssign,
  canPriority,
  canEscalate,
  canClose,
  canNotes,
  canDeadlines,
}: {
  complaintId: string;
  status: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
  canAssign: boolean;
  canPriority: boolean;
  canEscalate: boolean;
  canClose: boolean;
  canNotes: boolean;
  canDeadlines: boolean;
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
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      {canManage || canClose ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void run(() =>
              transitionComplaint({
                accessToken,
                organisationId,
                role,
                complaintId,
                body: {
                  status: String(form.get("status")),
                  note: String(form.get("note") || ""),
                  resolution_summary: String(form.get("resolution_summary") || "") || undefined,
                  tenant_visible_summary:
                    String(form.get("tenant_visible_summary") || "") || undefined,
                },
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Status transition</p>
          <select name="status" className="w-full rounded border px-3 py-2 text-sm" defaultValue={status}>
            <option value="acknowledged">Acknowledged</option>
            <option value="under_review">Under review</option>
            <option value="investigation">Investigation</option>
            <option value="awaiting_information">Awaiting information</option>
            <option value="escalated">Escalated</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
            <option value="reopened">Reopened</option>
            <option value="withdrawn">Withdrawn</option>
          </select>
          <textarea name="note" rows={2} placeholder="Explanation / note" className="w-full rounded border px-3 py-2 text-sm" />
          <textarea
            name="resolution_summary"
            rows={2}
            placeholder="Internal resolution summary (optional)"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <textarea
            name="tenant_visible_summary"
            rows={2}
            placeholder="Tenant-visible summary (optional)"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <button type="submit" disabled={pending} className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white">
            Apply status
          </button>
        </form>
      ) : null}

      {canPriority ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void run(() =>
              changeComplaintPriority({
                accessToken,
                organisationId,
                role,
                complaintId,
                priority: String(form.get("priority")),
                reason: String(form.get("reason") || ""),
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Change priority</p>
          <select name="priority" className="w-full rounded border px-3 py-2 text-sm" defaultValue="normal">
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
          <input name="reason" required placeholder="Reason" className="w-full rounded border px-3 py-2 text-sm" />
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm">
            Update priority
          </button>
        </form>
      ) : null}

      {canAssign ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const raw = String(form.get("assigned_user_id") || "").trim();
            void run(() =>
              assignComplaint({
                accessToken,
                organisationId,
                role,
                complaintId,
                assignedUserId: raw || null,
                note: String(form.get("note") || ""),
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Assign</p>
          <input
            name="assigned_user_id"
            placeholder="Assignee user UUID"
            className="w-full rounded border px-3 py-2 text-sm font-mono"
          />
          <input name="note" placeholder="Note" className="w-full rounded border px-3 py-2 text-sm" />
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm">
            Save assignment
          </button>
        </form>
      ) : null}

      {canNotes ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void run(() =>
              addComplaintNote({
                accessToken,
                organisationId,
                role,
                complaintId,
                body: {
                  body: String(form.get("body") || ""),
                  visibility: String(form.get("visibility") || "internal"),
                  is_follow_up: form.get("is_follow_up") === "on",
                },
              }),
            );
            event.currentTarget.reset();
          }}
        >
          <p className="text-sm font-medium">Investigation / follow-up note</p>
          <textarea name="body" required rows={3} className="w-full rounded border px-3 py-2 text-sm" />
          <select name="visibility" className="w-full rounded border px-3 py-2 text-sm" defaultValue="internal">
            <option value="internal">Internal only</option>
            <option value="tenant_visible">Tenant visible</option>
          </select>
          <label className="flex items-center gap-2 text-sm">
            <input name="is_follow_up" type="checkbox" /> Follow-up action
          </label>
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm">
            Add note
          </button>
        </form>
      ) : null}

      {canDeadlines ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const responseDue = String(form.get("response_due_at") || "");
            void run(() =>
              updateComplaintDeadlines({
                accessToken,
                organisationId,
                role,
                complaintId,
                responseDueAt: responseDue ? new Date(responseDue).toISOString() : undefined,
                reason: String(form.get("reason") || ""),
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Update operational deadline</p>
          <input name="response_due_at" type="datetime-local" className="w-full rounded border px-3 py-2 text-sm" />
          <input name="reason" required placeholder="Reason" className="w-full rounded border px-3 py-2 text-sm" />
          <p className="text-xs text-slate-500">Operational target only — not a statutory deadline.</p>
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm">
            Update deadline
          </button>
        </form>
      ) : null}

      {canEscalate ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void run(() =>
              escalateComplaint({
                accessToken,
                organisationId,
                role,
                complaintId,
                reason: String(form.get("reason") || ""),
                idempotencyKey: String(form.get("idempotency_key") || "") || undefined,
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Escalate</p>
          <textarea name="reason" required rows={2} className="w-full rounded border px-3 py-2 text-sm" />
          <input
            name="idempotency_key"
            placeholder="Optional idempotency key"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <button type="submit" disabled={pending} className="rounded bg-amber-700 px-3 py-1.5 text-sm text-white">
            Escalate complaint
          </button>
        </form>
      ) : null}
    </div>
  );
}
