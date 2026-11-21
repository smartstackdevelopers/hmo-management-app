"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
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
      className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
      aria-labelledby="maintenance-form-title"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const propertyId = String(form.get("property_id") || "").trim();
        if (!propertyId) {
          setError("Please enter the property reference.");
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
          .catch((err) => setError(err instanceof Error ? err.message : "We couldn't send your repair. Please try again."))
          .finally(() => setPending(false));
      }}
    >
      <div>
        <h2 id="maintenance-form-title" className="text-base font-semibold text-slate-900">
          What&apos;s the problem?
        </h2>
        <p className="mt-0.5 text-sm text-slate-500">A short title and a clear description help us send the right person.</p>
      </div>
      <div className="space-y-4">
        <div>
          <label htmlFor="maintenance-title" className={labelClass}>
            Title
          </label>
          <input
            id="maintenance-title"
            name="title"
            required
            aria-required="true"
            placeholder="For example, boiler pressure low"
            className={`mt-1.5 ${inputClass}`}
          />
        </div>
        <div>
          <label htmlFor="maintenance-description" className={labelClass}>
            Description
          </label>
          <textarea
            id="maintenance-description"
            name="description"
            required
            aria-required="true"
            rows={5}
            className={`mt-1.5 ${inputClass} h-auto py-2`}
          />
          <p className="mt-1.5 text-xs text-slate-500">Include where it is, when it started and anything you&apos;ve tried.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="maintenance-category" className={labelClass}>
              Category
            </label>
            <select id="maintenance-category" name="category_code" defaultValue="general" className={`mt-1.5 ${inputClass}`}>
              {categories.length === 0 ? (
                <option value="general">General</option>
              ) : (
                categories.map((c) => (
                  <option key={c.id} value={c.code}>
                    {c.title}
                  </option>
                ))
              )}
            </select>
          </div>
          <div>
            <label htmlFor="maintenance-priority" className={labelClass}>
              Priority
            </label>
            <select id="maintenance-priority" name="priority" defaultValue="normal" className={`mt-1.5 ${inputClass}`}>
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
              {!tenantMode ? <option value="emergency">Emergency (staff only)</option> : null}
            </select>
          </div>
        </div>
      </div>

      <div className="space-y-4 border-t border-slate-100 pt-6">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Where is it?</h3>
          <p className="mt-0.5 text-sm text-slate-500">Use the references shown on the property or room page.</p>
        </div>
        <div>
          <label htmlFor="maintenance-property-id" className={labelClass}>
            Property reference
          </label>
          <input
            id="maintenance-property-id"
            name="property_id"
            required
            aria-required="true"
            defaultValue={defaultPropertyId}
            aria-invalid={error?.includes("property") ? true : undefined}
            aria-describedby={error ? formErrorId : undefined}
            className={`mt-1.5 ${inputClass}`}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="maintenance-room-id" className={labelClass}>
              Room reference <span className="font-normal text-slate-500">(optional)</span>
            </label>
            <input id="maintenance-room-id" name="room_id" className={`mt-1.5 ${inputClass}`} />
          </div>
          {!tenantMode ? (
            <div>
              <label htmlFor="maintenance-tenant-id" className={labelClass}>
                Tenant reference <span className="font-normal text-slate-500">(optional)</span>
              </label>
              <input id="maintenance-tenant-id" name="tenant_id" defaultValue={defaultTenantId} className={`mt-1.5 ${inputClass}`} />
            </div>
          ) : null}
        </div>
        {!tenantMode ? (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" name="requires_approval" className="h-4 w-4 rounded border-slate-300 text-brand-700" />
            Needs approval before work starts
          </label>
        ) : null}
      </div>

      <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
        This form isn&apos;t for emergencies. Only staff can set emergency priority and they&apos;ll review every report. If
        anyone is in immediate danger, contact the emergency services.
      </p>
      {error ? (
        <p id={formErrorId} role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-5">
        <Link href="/dashboard/maintenance" className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} aria-busy={pending} className={btnPrimary}>
          {pending ? "Sending…" : "Send repair report"}
        </button>
      </div>
    </form>
  );
}
