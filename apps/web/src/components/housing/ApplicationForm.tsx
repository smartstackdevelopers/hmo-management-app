"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui/primitives";
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
      className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
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
      <div>
        <label htmlFor="application-tenant-id" className={labelClass}>
          Tenant ID
        </label>
        <input id="application-tenant-id" name="tenant_id" required className={`mt-1.5 ${inputClass}`} />
      </div>
      <div>
        <label htmlFor="application-requirements" className={labelClass}>
          Housing requirements
        </label>
        <textarea
          id="application-requirements"
          name="housing_requirements"
          required
          rows={4}
          className={`mt-1.5 ${inputClass} h-auto py-2`}
        />
      </div>
      <div>
        <label htmlFor="application-accommodation" className={labelClass}>
          Accommodation type
        </label>
        <input id="application-accommodation" name="accommodation_type" className={`mt-1.5 ${inputClass}`} />
      </div>
      <div>
        <label htmlFor="application-property" className={labelClass}>
          Preferred property ID <span className="font-normal text-slate-500">(optional)</span>
        </label>
        <input id="application-property" name="preferred_property_id" className={`mt-1.5 ${inputClass}`} />
      </div>
      <div>
        <label htmlFor="application-household" className={labelClass}>
          Household summary
        </label>
        <textarea id="application-household" name="household_summary" rows={2} className={`mt-1.5 ${inputClass} h-auto py-2`} />
      </div>
      <div>
        <label htmlFor="application-supporting" className={labelClass}>
          Supporting information
        </label>
        <textarea
          id="application-supporting"
          name="supporting_information"
          rows={2}
          className={`mt-1.5 ${inputClass} h-auto py-2`}
        />
      </div>
      <div>
        <label htmlFor="application-priority" className={labelClass}>
          Priority
        </label>
        <select id="application-priority" name="priority" defaultValue="normal" className={`mt-1.5 ${inputClass}`}>
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input name="submit" type="checkbox" className="h-4 w-4 rounded border-slate-300 text-brand-700" />
        Submit immediately
      </label>
      {error ? (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end border-t border-slate-100 pt-5">
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Save application"}
        </button>
      </div>
    </form>
  );
}
