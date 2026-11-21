"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
import {
  addToWaitingList,
  decideApplication,
  requestApplicationInformation,
  submitApplication,
} from "@/lib/housingApi";

const field = `mt-1.5 ${inputClass}`;
const area = `mt-1.5 ${inputClass} h-auto py-2`;

export function ApplicationReviewActions({
  applicationId,
  status,
  onWaitingList,
  accessToken,
  organisationId,
  role,
  canReview,
}: {
  applicationId: string;
  status: string;
  onWaitingList: boolean;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canReview: boolean;
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
    <div className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
      {status === "draft" ? (
        <button
          type="button"
          disabled={pending}
          className={btnPrimary}
          onClick={() =>
            void run(() =>
              submitApplication({ accessToken, organisationId, role, applicationId }),
            )
          }
        >
          Submit application
        </button>
      ) : null}

      {canReview && ["submitted", "under_review", "information_required"].includes(status) ? (
        <>
          <form
            className="space-y-2"
            onSubmit={(event) => {
              event.preventDefault();
              const form = new FormData(event.currentTarget);
              void run(() =>
                decideApplication({
                  accessToken,
                  organisationId,
                  role,
                  applicationId,
                  body: {
                    decision: String(form.get("decision") || "approved"),
                    decision_notes: String(form.get("decision_notes") || ""),
                    add_to_waiting_list: form.get("add_to_waiting_list") === "on",
                  },
                }),
              );
            }}
          >
            <p className={labelClass}>Record decision</p>
            <select name="decision" defaultValue="approved" className={field}>
              <option value="approved">Approve</option>
              <option value="rejected">Reject</option>
            </select>
            <textarea
              name="decision_notes"
              required
              rows={3}
              placeholder="Decision notes / reason"
              className={area}
            />
            <label className="flex items-center gap-2 text-sm">
              <input name="add_to_waiting_list" type="checkbox" />
              Add to waiting list on approval
            </label>
            <button type="submit" disabled={pending} className={btnPrimary}>
              Save decision
            </button>
          </form>
          <form
            className="space-y-2 border-t border-slate-100 pt-3"
            onSubmit={(event) => {
              event.preventDefault();
              const form = new FormData(event.currentTarget);
              void run(() =>
                requestApplicationInformation({
                  accessToken,
                  organisationId,
                  role,
                  applicationId,
                  notes: String(form.get("notes") || ""),
                }),
              );
            }}
          >
            <p className={labelClass}>Request information</p>
            <textarea name="notes" required rows={2} className={area} />
            <button type="submit" disabled={pending} className={btnSecondary}>
              Request more information
            </button>
          </form>
        </>
      ) : null}

      {canReview && status === "approved" && !onWaitingList ? (
        <button
          type="button"
          disabled={pending}
          className={btnSecondary}
          onClick={() =>
            void run(() =>
              addToWaitingList({
                accessToken,
                organisationId,
                role,
                body: { application_id: applicationId },
              }),
            )
          }
        >
          Add to waiting list
        </button>
      ) : null}

      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
