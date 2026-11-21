"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "@/components/ui/primitives";
import {
  createCommunityService,
  updateCommunityService,
  type CommunityService,
} from "@/lib/communityDirectoryApi";

const CATEGORIES = [
  { value: "food_bank", label: "Food bank" },
  { value: "kitchen", label: "Community kitchen" },
  { value: "clothing_bank", label: "Clothing bank" },
  { value: "local_service", label: "Local service" },
];

export function CommunityServiceForm({
  accessToken,
  organisationId,
  role,
  existing,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  existing?: CommunityService;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [category, setCategory] = useState(existing?.category ?? "food_bank");

  return (
    <form
      className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        const body = {
          category: String(form.get("category") || ""),
          name: String(form.get("name") || ""),
          description: String(form.get("description") || "") || null,
          address_line: String(form.get("address_line") || "") || null,
          opening_days: String(form.get("opening_days") || "") || null,
          opening_hours: String(form.get("opening_hours") || "") || null,
          eligibility: String(form.get("eligibility") || "") || null,
          referral_requirements: String(form.get("referral_requirements") || "") || null,
          contact: String(form.get("contact") || "") || null,
          service_instructions: String(form.get("service_instructions") || "") || null,
          clothing_service_type:
            String(form.get("category") || "") === "clothing_bank"
              ? String(form.get("clothing_service_type") || "") || null
              : null,
          information_source: String(form.get("information_source") || "") || null,
          is_published: form.get("is_published") === "on",
        };
        try {
          if (existing) {
            await updateCommunityService({
              accessToken,
              organisationId,
              role,
              serviceId: existing.id,
              body,
            });
            router.push(`/dashboard/community-directory/${existing.id}`);
          } else {
            const created = await createCommunityService({
              accessToken,
              organisationId,
              role,
              body,
            });
            router.push(`/dashboard/community-directory/${created.id}`);
          }
          router.refresh();
        } catch {
          setError("We couldn't save this service. Check the name and category, then try again.");
        } finally {
          setPending(false);
        }
      }}
    >
      <div>
        <h2 className="text-base font-semibold text-slate-900">Service</h2>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="service-name" className={labelClass}>
            Name
          </label>
          <input id="service-name" name="name" required defaultValue={existing?.name ?? ""} className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="service-category" className={labelClass}>
            Category
          </label>
          <select
            id="service-category"
            name="category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className={inputClass}
            required
          >
            {CATEGORIES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="service-contact" className={labelClass}>
            Contact
          </label>
          <input id="service-contact" name="contact" defaultValue={existing?.contact ?? ""} className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="service-source" className={labelClass}>
            Information source
          </label>
          <input id="service-source" name="information_source" defaultValue={existing?.information_source ?? ""} className={inputClass} />
        </div>
      </div>
      <div className="space-y-4 border-t border-slate-100 pt-5">
        <h2 className="text-base font-semibold text-slate-900">Location & access</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label htmlFor="service-address" className={labelClass}>
              Address
            </label>
            <input id="service-address" name="address_line" defaultValue={existing?.address_line ?? ""} className={inputClass} />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="service-hours" className={labelClass}>
              Opening hours
            </label>
            <input id="service-hours" name="opening_hours" defaultValue={existing?.opening_hours ?? ""} className={inputClass} placeholder="Only if you have confirmed them" />
          </div>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="service-days" className={labelClass}>
            Opening days
          </label>
          <input id="service-days" name="opening_days" defaultValue={existing?.opening_days ?? ""} className={inputClass} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="service-description" className={labelClass}>
            Description
          </label>
          <textarea id="service-description" name="description" defaultValue={existing?.description ?? ""} rows={3} className={`${inputClass} h-auto py-2`} />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="service-eligibility" className={labelClass}>
            Eligibility
          </label>
          <textarea id="service-eligibility" name="eligibility" defaultValue={existing?.eligibility ?? ""} rows={2} className={`${inputClass} h-auto py-2`} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="service-referral" className={labelClass}>
            Referral requirements
          </label>
          <textarea id="service-referral" name="referral_requirements" defaultValue={existing?.referral_requirements ?? ""} rows={2} className={`${inputClass} h-auto py-2`} />
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="service-instructions" className={labelClass}>
          Service instructions
        </label>
        <textarea id="service-instructions" name="service_instructions" defaultValue={existing?.service_instructions ?? ""} rows={2} className={`${inputClass} h-auto py-2`} />
      </div>
      {category === "clothing_bank" ? (
        <div className="space-y-1.5">
          <label htmlFor="service-clothing" className={labelClass}>
            Clothing service type
          </label>
          <select id="service-clothing" name="clothing_service_type" defaultValue={existing?.clothing_service_type ?? ""} className={inputClass}>
            <option value="">Not specified</option>
            <option value="provides_clothing">Provides clothing to people in need</option>
            <option value="accepts_donations">Accepts clothing donations</option>
            <option value="both">Provides clothing and accepts donations</option>
          </select>
        </div>
      ) : null}
      <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
        <input name="is_published" type="checkbox" defaultChecked={existing?.is_published ?? false} className="h-4 w-4 rounded border-slate-300 text-brand-700 focus:ring-brand-600" />
        Publish to the tenant directory. Verification is still required.
      </label>
      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Link href={existing ? `/dashboard/community-directory/${existing.id}` : "/dashboard/community-directory"} className={btnSecondary}>
          Cancel
        </Link>
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : existing ? "Save changes" : "Publish service"}
        </button>
      </div>
    </form>
  );
}
