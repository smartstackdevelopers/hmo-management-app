"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createDailyLog } from "@/lib/supportApi";

const CATEGORIES = [
  "welfare_check",
  "keywork",
  "housing",
  "health",
  "safeguarding",
  "appointment",
  "phone_call",
  "email",
  "other",
];

export function DailyLogForm({
  accessToken,
  organisationId,
  role,
  defaultTenantId,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  defaultTenantId?: string;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <form
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        try {
          const log = await createDailyLog({
            accessToken,
            organisationId,
            role,
            body: {
              tenant_id: String(form.get("tenant_id") || ""),
              activity_category: String(form.get("activity_category") || ""),
              summary: String(form.get("summary") || ""),
              notes: String(form.get("notes") || ""),
              interaction_type: String(form.get("interaction_type") || "") || null,
              follow_up_required: form.get("follow_up_required") === "on",
              next_action: String(form.get("next_action") || "") || null,
            },
          });
          router.push(`/dashboard/caseload/${log.tenant_id}`);
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to create log");
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        <span className="font-medium text-forest-900">Tenant ID</span>
        <input
          name="tenant_id"
          required
          defaultValue={defaultTenantId}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block text-sm">
        <span className="font-medium text-forest-900">Activity category</span>
        <select
          name="activity_category"
          required
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          defaultValue="keywork"
        >
          {CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        <span className="font-medium text-forest-900">Summary</span>
        <input
          name="summary"
          required
          maxLength={255}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block text-sm">
        <span className="font-medium text-forest-900">Notes</span>
        <textarea
          name="notes"
          required
          rows={6}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block text-sm">
        <span className="font-medium text-forest-900">Interaction type</span>
        <select name="interaction_type" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
          <option value="">—</option>
          <option value="in_person">in_person</option>
          <option value="phone">phone</option>
          <option value="video">video</option>
          <option value="message">message</option>
          <option value="collateral">collateral</option>
          <option value="other">other</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" name="follow_up_required" />
        Follow-up required
      </label>
      <label className="block text-sm">
        <span className="font-medium text-forest-900">Next action</span>
        <textarea name="next_action" rows={2} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-teal-700 px-4 py-2 text-sm text-white disabled:opacity-60"
      >
        {pending ? "Saving…" : "Save daily log"}
      </button>
    </form>
  );
}
