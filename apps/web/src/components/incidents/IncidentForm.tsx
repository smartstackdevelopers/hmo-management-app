"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-5"
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
          setError(err instanceof Error ? err.message : "Failed to create incident");
        } finally {
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        Title
        <input name="title" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Category
        <input name="category" defaultValue="general" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Occurred at
        <input name="occurred_at" type="datetime-local" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Severity
        <select name="severity" defaultValue="normal" className="mt-1 w-full rounded border px-3 py-2">
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </label>
      <label className="block text-sm">
        Location
        <input name="location" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Tenant ID (optional)
        <input name="tenant_id" className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Description
        <textarea name="description" required rows={4} className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Immediate actions
        <textarea name="immediate_actions" rows={3} className="mt-1 w-full rounded border px-3 py-2" />
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
        {pending ? "Saving…" : "Save incident"}
      </button>
    </form>
  );
}
