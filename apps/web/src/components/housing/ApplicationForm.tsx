"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createApplication } from "@/lib/housingApi";

export function ApplicationForm({
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
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-5"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        try {
          const app = await createApplication({
            accessToken,
            organisationId,
            role,
            body: {
              tenant_id: String(form.get("tenant_id") || ""),
              housing_requirements: String(form.get("housing_requirements") || ""),
              accommodation_type: String(form.get("accommodation_type") || "") || null,
              household_summary: String(form.get("household_summary") || "") || null,
              supporting_information: String(form.get("supporting_information") || "") || null,
              priority: String(form.get("priority") || "normal"),
              preferred_property_id: String(form.get("preferred_property_id") || "") || null,
              submit: form.get("submit") === "on",
            },
          });
          router.push(`/dashboard/housing-applications/${app.id}`);
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to create application");
        } finally {
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        Tenant ID
        <input name="tenant_id" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Housing requirements
        <textarea name="housing_requirements" required rows={4} className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Accommodation type
        <input name="accommodation_type" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Preferred property ID (optional)
        <input name="preferred_property_id" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Household summary
        <textarea name="household_summary" rows={2} className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Supporting information
        <textarea name="supporting_information" rows={2} className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Priority
        <select name="priority" defaultValue="normal" className="mt-1 w-full rounded border px-3 py-2">
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input name="submit" type="checkbox" />
        Submit immediately
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
      >
        {pending ? "Saving…" : "Save application"}
      </button>
    </form>
  );
}
