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
import { btnPrimary, btnSecondary, humanize, inputClass } from "@/components/ui/primitives";

const field = `mt-1.5 ${inputClass}`;
const area = `mt-1.5 ${inputClass} h-auto py-2`;
const section = "space-y-2 border-t border-slate-100 pt-5 first:border-t-0 first:pt-0";
const heading = "text-sm font-semibold text-slate-900";
const smallBtn = `mt-1 ${btnSecondary} h-9`;

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
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-5">
      {error ? <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

      {canManage ? (
        <button
          type="button"
          disabled={pending}
          className={smallBtn}
          onClick={() =>
            void run(() => seedMaintenanceDefaults({ accessToken, organisationId, role }))
          }
        >
          Set up default categories and safety guidance
        </button>
      ) : null}

      {isTenant ? (
        <form
          className={section}
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
          <p className={heading}>Cancel request</p>
          <textarea name="note" required rows={2} placeholder="Tell us why you are cancelling" className={area} />
          <button type="submit" disabled={pending} className={`${smallBtn} text-red-700`}>
            Cancel
          </button>
        </form>
      ) : null}

      {((canManage && !isTenant) || (isContractor && !isTenant)) ? (
        <form
          className={section}
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
          <p className={heading}>Update status</p>
          <select name="status" className={field} defaultValue={status}>
            {(canManage ? STAFF_STATUSES : ["in_progress", "on_hold"]).map((s) => (
                <option key={s} value={s}>
                  {humanize(s)}
                </option>
              ))}
          </select>
          <textarea name="note" rows={2} placeholder="Add a note or reason (if needed)" className={area} />
          <button type="submit" disabled={pending} className={`mt-1 ${btnPrimary} h-9`}>
            Apply status
          </button>
        </form>
      ) : null}

      {canPriority ? (
        <form
          className={section}
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
          <p className={heading}>Change priority</p>
          <select name="priority" className={field} defaultValue="normal">
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
            <option value="emergency">Emergency</option>
          </select>
          <input name="reason" required placeholder="Reason for the change" className={field} />
          <button type="submit" disabled={pending} className={smallBtn}>
            Update priority
          </button>
        </form>
      ) : null}

      {canAssign ? (
        <form
          className={section}
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
          <p className={heading}>Assign</p>
          <input
            name="assigned_user_id"
            placeholder="Person to assign"
            className={field}
          />
          <input name="note" placeholder="Note (optional)" className={field} />
          <button type="submit" disabled={pending} className={smallBtn}>
            Save assignment
          </button>
        </form>
      ) : null}

      {canApprove ? (
        <form
          className={section}
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
          <p className={heading}>Approve or reject</p>
          <select name="decision" className={field}>
            <option value="approved">Approve</option>
            <option value="rejected">Reject</option>
          </select>
          <textarea name="reason" rows={2} placeholder="Reason (required for rejection)" className={area} />
          <button type="submit" disabled={pending} className={smallBtn}>
            Submit decision
          </button>
        </form>
      ) : null}

      {canSchedule ? (
        <form
          className={section}
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
          <p className={heading}>Schedule visit</p>
          <input
            name="scheduled_at"
            type="datetime-local"
            required
            className={field}
          />
          <input name="timezone" defaultValue="Europe/London" className={field} />
          <input
            name="assignee_user_id"
            placeholder="Person to send (optional)"
            className={field}
          />
          <button type="submit" disabled={pending} className={smallBtn}>
            Schedule
          </button>
        </form>
      ) : null}

      {canComplete ? (
        <form
          className={section}
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
          <p className={heading}>Mark work complete</p>
          <textarea name="work_notes" required rows={3} className={area} />
          <textarea name="completion_summary" rows={2} placeholder="Short summary (optional)" className={area} />
          <button
            type="submit"
            disabled={pending}
            className={`mt-1 h-9 ${((canManage && !isTenant) || (isContractor && !isTenant)) ? btnSecondary : btnPrimary}`}
          >
            Mark completed
          </button>
        </form>
      ) : null}

      {canNotes ? (
        <form
          className={section}
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
          <p className={heading}>Notes</p>
          <select name="visibility" className={field} defaultValue="internal">
            <option value="internal">Internal</option>
            <option value="tenant_visible">Visible to tenant</option>
          </select>
          <textarea name="body" required rows={3} className={area} />
          <button type="submit" disabled={pending} className={smallBtn}>
            Add note
          </button>
        </form>
      ) : null}

      {canUploadPhoto ? (
        <form
          className={section}
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const file = form.get("file");
            if (!(file instanceof File) || file.size === 0) {
              setError("Choose a photo to upload.");
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
          <p className={heading}>Upload photo</p>
          <input name="file" type="file" accept="image/*" required className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-brand-700 hover:file:bg-brand-100" />
          <select name="photo_kind" className={field}>
            <option value="problem">Problem</option>
            <option value="completion">Completion</option>
          </select>
          <input name="caption" placeholder="Caption" className={field} />
          <button type="submit" disabled={pending} className={smallBtn}>
            Upload
          </button>
        </form>
      ) : null}
    </div>
  );
}
