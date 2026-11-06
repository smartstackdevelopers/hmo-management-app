"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  addToWaitingList,
  decideApplication,
  requestApplicationInformation,
  submitApplication,
} from "@/lib/housingApi";

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
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      {status === "draft" ? (
        <button
          type="button"
          disabled={pending}
          className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white"
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
            <p className="text-sm font-medium text-forest-900">Record decision</p>
            <select name="decision" defaultValue="approved" className="w-full rounded border px-3 py-2 text-sm">
              <option value="approved">Approve</option>
              <option value="rejected">Reject</option>
            </select>
            <textarea
              name="decision_notes"
              required
              rows={3}
              placeholder="Decision notes / reason"
              className="w-full rounded border px-3 py-2 text-sm"
            />
            <label className="flex items-center gap-2 text-sm">
              <input name="add_to_waiting_list" type="checkbox" />
              Add to waiting list on approval
            </label>
            <button type="submit" disabled={pending} className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white">
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
            <p className="text-sm font-medium text-forest-900">Request information</p>
            <textarea name="notes" required rows={2} className="w-full rounded border px-3 py-2 text-sm" />
            <button type="submit" disabled={pending} className="rounded border border-slate-300 px-3 py-1.5 text-sm">
              Request more information
            </button>
          </form>
        </>
      ) : null}

      {canReview && status === "approved" && !onWaitingList ? (
        <button
          type="button"
          disabled={pending}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm"
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
