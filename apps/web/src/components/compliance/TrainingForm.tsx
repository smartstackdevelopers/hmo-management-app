"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
import { createTraining } from "@/lib/complianceApi";

export function TrainingForm({
  accessToken,
  organisationId,
  role,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <form
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        const completion = String(form.get("completion_date") || "");
        const expiry = String(form.get("expiry_date") || "");
        try {
          await createTraining({
            accessToken,
            organisationId,
            role,
            body: {
              staff_user_id: String(form.get("staff_user_id") || ""),
              title: String(form.get("title") || ""),
              category: String(form.get("category") || "general"),
              provider: String(form.get("provider") || "") || null,
              status: String(form.get("status") || "not_started"),
              completion_date: completion || null,
              expiry_date: expiry || null,
              notes: String(form.get("notes") || "") || null,
            },
          });
          router.push("/dashboard/training");
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "We couldn't save this training record. Please try again.");
        } finally {
          setPending(false);
        }
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5 sm:col-span-2">
          <label htmlFor="training-staff" className={labelClass}>
            Staff reference
          </label>
          <input id="training-staff" name="staff_user_id" required className={`${inputClass} font-mono`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="training-title" className={labelClass}>
            Title
          </label>
          <input id="training-title" name="title" required className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="training-category" className={labelClass}>
            Category
          </label>
          <input id="training-category" name="category" defaultValue="general" className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="training-provider" className={labelClass}>
            Provider
          </label>
          <input id="training-provider" name="provider" className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="training-status" className={labelClass}>
            Status
          </label>
          <select id="training-status" name="status" defaultValue="completed" className={inputClass}>
            <option value="not_started">Not started</option>
            <option value="in_progress">In progress</option>
            <option value="completed">Completed</option>
            <option value="exempt">Exempt</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="training-completed" className={labelClass}>
            Completion date
          </label>
          <input id="training-completed" name="completion_date" type="date" className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="training-expiry" className={labelClass}>
            Expiry date
          </label>
          <input id="training-expiry" name="expiry_date" type="date" className={inputClass} />
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="training-notes" className={labelClass}>
          Notes
        </label>
        <textarea id="training-notes" name="notes" rows={3} className={`${inputClass} h-auto py-2`} />
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href="/dashboard/training" className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Save training record"}
        </button>
      </div>
    </form>
  );
}
