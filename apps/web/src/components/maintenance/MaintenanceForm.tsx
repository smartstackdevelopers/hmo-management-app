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

  return (
    <form
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-4"
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
      <label className="block text-sm">
        Title
        <input name="title" required className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Description
        <textarea name="description" required rows={5} className="mt-1 w-full rounded border px-3 py-2" />
      </label>
      <label className="block text-sm">
        Property ID
        <input
          name="property_id"
          required
          defaultValue={defaultPropertyId}
          className="mt-1 w-full rounded border px-3 py-2 font-mono text-sm"
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
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
      >
        {pending ? "Submitting…" : "Submit request"}
      </button>
    </form>
  );
}
