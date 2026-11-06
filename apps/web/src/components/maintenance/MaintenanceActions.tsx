"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  addMaintenanceNote,
  assignMaintenance,
  changeMaintenancePriority,
  completeMaintenanceWork,
  maintenanceApproval,
  scheduleMaintenanceVisit,
  seedMaintenanceDefaults,
  transitionMaintenance,
  uploadMaintenancePhotoMultipart,
} from "@/lib/maintenanceApi";

const STAFF_STATUSES = [
  "acknowledged",
  "under_review",
  "awaiting_approval",
  "approved",
  "assigned",
  "scheduled",
  "in_progress",
  "awaiting_parts",
  "on_hold",
  "cancelled",
  "closed",
  "reopened",
];

export function MaintenanceActions({
  requestId,
  status,
  accessToken,
  organisationId,
  role,
  canManage,
  canAssign,
  canPriority,
  canSchedule,
  canApprove,
  canNotes,
  canComplete,
  canUploadPhoto,
  isTenant,
  isContractor,
}: {
  requestId: string;
  status: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
  canAssign: boolean;
  canPriority: boolean;
  canSchedule: boolean;
  canApprove: boolean;
  canNotes: boolean;
  canComplete: boolean;
  canUploadPhoto: boolean;
  isTenant: boolean;
  isContractor: boolean;
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

      {canManage ? (
        <button
          type="button"
          disabled={pending}
          className="rounded border px-3 py-1.5 text-sm"
          onClick={() =>
            void run(() => seedMaintenanceDefaults({ accessToken, organisationId, role }))
          }
        >
          Seed maintenance defaults (categories &amp; emergency placeholders)
        </button>
      ) : null}

      {isTenant ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void run(() =>
              transitionMaintenance({
                accessToken,
                organisationId,
                role,
                requestId,
                body: {
                  status: "cancelled",
                  note: String(form.get("note") || ""),
                },
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Cancel request</p>
          <textarea name="note" required rows={2} placeholder="Reason" className="w-full rounded border px-3 py-2 text-sm" />
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm text-red-800">
            Cancel
          </button>
        </form>
      ) : null}

      {((canManage && !isTenant) || (isContractor && !isTenant)) ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void run(() =>
              transitionMaintenance({
                accessToken,
                organisationId,
                role,
                requestId,
                body: {
                  status: String(form.get("status")),
                  note: String(form.get("note") || "") || undefined,
                },
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Status transition</p>
          <select name="status" className="w-full rounded border px-3 py-2 text-sm" defaultValue={status}>
            {(canManage ? STAFF_STATUSES : ["in_progress", "on_hold"]).map((s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ))}
          </select>
          <textarea name="note" rows={2} placeholder="Note / reason where required" className="w-full rounded border px-3 py-2 text-sm" />
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
              changeMaintenancePriority({
                accessToken,
                organisationId,
                role,
                requestId,
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
            <option value="emergency">Emergency</option>
          </select>
          <input name="reason" required placeholder="Reason (required)" className="w-full rounded border px-3 py-2 text-sm" />
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
              assignMaintenance({
                accessToken,
                organisationId,
                role,
                requestId,
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

      {canApprove ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const decision = String(form.get("decision")) as "approved" | "rejected";
            void run(() =>
              maintenanceApproval({
                accessToken,
                organisationId,
                role,
                requestId,
                decision,
                reason: String(form.get("reason") || "") || undefined,
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Approval</p>
          <select name="decision" className="w-full rounded border px-3 py-2 text-sm">
            <option value="approved">Approve</option>
            <option value="rejected">Reject</option>
          </select>
          <textarea name="reason" rows={2} placeholder="Reason (required for rejection)" className="w-full rounded border px-3 py-2 text-sm" />
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm">
            Submit decision
          </button>
        </form>
      ) : null}

      {canSchedule ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const raw = String(form.get("assignee_user_id") || "").trim();
            void run(() =>
              scheduleMaintenanceVisit({
                accessToken,
                organisationId,
                role,
                requestId,
                scheduled_at: new Date(String(form.get("scheduled_at"))).toISOString(),
                timezone: String(form.get("timezone") || "Europe/London"),
                assignee_user_id: raw || null,
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Schedule visit</p>
          <input
            name="scheduled_at"
            type="datetime-local"
            required
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <input name="timezone" defaultValue="Europe/London" className="w-full rounded border px-3 py-2 text-sm" />
          <input
            name="assignee_user_id"
            placeholder="Assignee user UUID (optional)"
            className="w-full rounded border px-3 py-2 text-sm font-mono"
          />
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm">
            Schedule
          </button>
        </form>
      ) : null}

      {canComplete ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void run(() =>
              completeMaintenanceWork({
                accessToken,
                organisationId,
                role,
                requestId,
                work_notes: String(form.get("work_notes") || ""),
                completion_summary: String(form.get("completion_summary") || "") || undefined,
              }),
            );
          }}
        >
          <p className="text-sm font-medium">Record completion</p>
          <textarea name="work_notes" required rows={3} className="w-full rounded border px-3 py-2 text-sm" />
          <textarea name="completion_summary" rows={2} placeholder="Short summary (optional)" className="w-full rounded border px-3 py-2 text-sm" />
          <button type="submit" disabled={pending} className="rounded bg-emerald-800 px-3 py-1.5 text-sm text-white">
            Mark completed
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
              addMaintenanceNote({
                accessToken,
                organisationId,
                role,
                requestId,
                body: {
                  body: String(form.get("body") || ""),
                  visibility: String(form.get("visibility") || "internal"),
                },
              }),
            );
            event.currentTarget.reset();
          }}
        >
          <p className="text-sm font-medium">Notes</p>
          <select name="visibility" className="w-full rounded border px-3 py-2 text-sm" defaultValue="internal">
            <option value="internal">Internal</option>
            <option value="tenant_visible">Tenant visible</option>
          </select>
          <textarea name="body" required rows={3} className="w-full rounded border px-3 py-2 text-sm" />
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm">
            Add note
          </button>
        </form>
      ) : null}

      {canUploadPhoto ? (
        <form
          className="space-y-2"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const file = form.get("file");
            if (!(file instanceof File) || file.size === 0) {
              setError("Choose a file");
              return;
            }
            void run(() =>
              uploadMaintenancePhotoMultipart({
                accessToken,
                organisationId,
                role,
                requestId,
                file,
                caption: String(form.get("caption") || "") || undefined,
                photoKind: String(form.get("photo_kind") || "problem"),
              }),
            );
            event.currentTarget.reset();
          }}
        >
          <p className="text-sm font-medium">Upload photo</p>
          <input name="file" type="file" accept="image/*" required className="w-full text-sm" />
          <select name="photo_kind" className="w-full rounded border px-3 py-2 text-sm">
            <option value="problem">Problem</option>
            <option value="completion">Completion</option>
          </select>
          <input name="caption" placeholder="Caption" className="w-full rounded border px-3 py-2 text-sm" />
          <button type="submit" disabled={pending} className="rounded border px-3 py-1.5 text-sm">
            Upload
          </button>
        </form>
      ) : null}
    </div>
  );
}
