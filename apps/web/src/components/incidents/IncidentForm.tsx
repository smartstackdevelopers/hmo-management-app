"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
import { createIncident } from "@/lib/incidentsApi";

export function IncidentForm({
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
        try {
          const incident = await createIncident({
            accessToken,
            organisationId,
            role,
            body: {
              title: String(form.get("title") || ""),
              category: String(form.get("category") || "general"),
              description: String(form.get("description") || ""),
              occurred_at: new Date(String(form.get("occurred_at") || "")).toISOString(),
              severity: String(form.get("severity") || "normal"),
              location: String(form.get("location") || "") || null,
              immediate_actions: String(form.get("immediate_actions") || "") || null,
              tenant_id: String(form.get("tenant_id") || "") || null,
              submit: form.get("submit") === "on",
            },
          });
          router.push(`/dashboard/incidents/${incident.id}`);
          router.refresh();
        } catch (err) {
          setError(err instanceof Error ? err.message : "We couldn't save this incident. Please try again.");
        } finally {
          setPending(false);
        }
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5 sm:col-span-2">
          <label htmlFor="incident-title" className={labelClass}>
            Title
          </label>
          <input id="incident-title" name="title" required className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="incident-category" className={labelClass}>
            Category
          </label>
          <input id="incident-category" name="category" defaultValue="general" className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="incident-severity" className={labelClass}>
            Severity
          </label>
          <select id="incident-severity" name="severity" defaultValue="normal" className={inputClass}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="incident-when" className={labelClass}>
            Occurred
          </label>
          <input id="incident-when" name="occurred_at" type="datetime-local" required className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="incident-location" className={labelClass}>
            Location
          </label>
          <input id="incident-location" name="location" className={inputClass} />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <label htmlFor="incident-tenant" className={labelClass}>
            Tenant reference
          </label>
          <input id="incident-tenant" name="tenant_id" className={`${inputClass} font-mono`} />
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="incident-description" className={labelClass}>
          Description
        </label>
        <textarea id="incident-description" name="description" required rows={4} className={`${inputClass} h-auto py-2`} />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="incident-actions" className={labelClass}>
          Immediate actions
        </label>
        <textarea id="incident-actions" name="immediate_actions" rows={3} className={`${inputClass} h-auto py-2`} />
      </div>
      <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
        <input name="submit" type="checkbox" className="h-4 w-4 rounded border-slate-300 text-brand-700 focus:ring-brand-600" />
        Submit immediately
      </label>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href="/dashboard/incidents" className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Save incident"}
        </button>
      </div>
    </form>
  );
}
