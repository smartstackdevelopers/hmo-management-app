"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createMaintenanceRequest, listMaintenanceCategories, type MaintenanceCategory } from "@/lib/maintenanceApi";

export function MaintenanceForm({
  accessToken,
  organisationId,
  role,
  defaultPropertyId,
  defaultTenantId,
  tenantMode,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  defaultPropertyId?: string;
  defaultTenantId?: string;
  tenantMode?: boolean;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [categories, setCategories] = useState<MaintenanceCategory[]>([]);

  useEffect(() => {
    void listMaintenanceCategories({ accessToken, organisationId, role })
      .then(setCategories)
      .catch(() => setCategories([]));
  }, [accessToken, organisationId, role]);

  const formErrorId = "maintenance-form-error";

  return (
    <form
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-4"
      aria-labelledby="maintenance-form-title"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const propertyId = String(form.get("property_id") || "").trim();
        if (!propertyId) {
          setError("Property ID is required");
          return;
        }
        setPending(true);
        setError(null);
        void createMaintenanceRequest({
          accessToken,
          organisationId,
          role,
          body: {
            title: String(form.get("title") || ""),
            description: String(form.get("description") || ""),
            category_code: String(form.get("category_code") || "general"),
            priority: String(form.get("priority") || "normal"),
            property_id: propertyId,
            room_id: String(form.get("room_id") || "").trim() || undefined,
            tenant_id: tenantMode ? undefined : String(form.get("tenant_id") || "").trim() || defaultTenantId,
            requires_approval: form.get("requires_approval") === "on",
          },
        })
          .then((row) => router.push(`/dashboard/maintenance/${row.id}`))
          .catch((err) => setError(err instanceof Error ? err.message : "Submit failed"))
          .finally(() => setPending(false));
      }}
    >
      <h2 id="maintenance-form-title" className="text-lg font-semibold text-forest-900">
        New maintenance request
      </h2>
      <label className="block text-sm">
        Title
        <input
          id="maintenance-title"
          name="title"
          required
          aria-required="true"
          className="mt-1 w-full rounded border px-3 py-2 focus:border-teal-700"
        />
      </label>
      <label className="block text-sm">
        Description
        <textarea
          id="maintenance-description"
          name="description"
          required
          aria-required="true"
          rows={5}
          className="mt-1 w-full rounded border px-3 py-2 focus:border-teal-700"
        />
      </label>
      <label className="block text-sm">
        Property ID
        <input
          id="maintenance-property-id"
          name="property_id"
          required
          aria-required="true"
          defaultValue={defaultPropertyId}
          aria-invalid={error?.includes("Property") ? true : undefined}
          aria-describedby={error ? formErrorId : undefined}
          className="mt-1 w-full rounded border px-3 py-2 font-mono text-sm focus:border-teal-700"
        />
      </label>
      <label className="block text-sm">
        Room ID (optional)
        <input name="room_id" className="mt-1 w-full rounded border px-3 py-2 font-mono text-sm" />
      </label>
      {!tenantMode ? (
        <label className="block text-sm">
          Tenant ID (support worker)
          <input
            name="tenant_id"
            defaultValue={defaultTenantId}
            className="mt-1 w-full rounded border px-3 py-2 font-mono text-sm"
          />
        </label>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          Category
          <select name="category_code" defaultValue="general" className="mt-1 w-full rounded border px-3 py-2">
            {categories.length === 0 ? (
              <option value="general">General (load categories or run seed-defaults)</option>
            ) : (
              categories.map((c) => (
                <option key={c.id} value={c.code}>
                  {c.title}
                </option>
              ))
            )}
          </select>
        </label>
        <label className="block text-sm">
          Priority
          <select name="priority" defaultValue="normal" className="mt-1 w-full rounded border px-3 py-2">
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
            {!tenantMode ? <option value="emergency">Emergency (staff only elsewhere)</option> : null}
          </select>
        </label>
      </div>
      {!tenantMode ? (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="requires_approval" /> Requires approval before work
        </label>
      ) : null}
      <p className="text-xs text-slate-500">
        Operational categories and priorities only. Tenants cannot set emergency priority here; staff must review and
        escalate if appropriate.
      </p>
      {error ? (
        <p id={formErrorId} role="alert" className="text-sm text-red-800">
          {error}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={pending}
        aria-busy={pending}
        className="min-h-11 rounded bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700 disabled:opacity-50"
      >
        {pending ? "Submitting…" : "Submit request"}
      </button>
    </form>
  );
}
