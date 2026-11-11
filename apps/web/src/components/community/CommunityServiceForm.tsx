"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-5"
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
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to save listing");
        } finally {
          setPending(false);
        }
      }}
    >
      <label className="block text-sm">
        Category
        <select
          name="category"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
          required
        >
          {CATEGORIES.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        Service name
        <input
          name="name"
          required
          defaultValue={existing?.name ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Description
        <textarea
          name="description"
          defaultValue={existing?.description ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
          rows={3}
        />
      </label>
      <label className="block text-sm">
        Address
        <input
          name="address_line"
          defaultValue={existing?.address_line ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Opening days
        <input
          name="opening_days"
          defaultValue={existing?.opening_days ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
          placeholder="e.g. Monday to Friday"
        />
      </label>
      <label className="block text-sm">
        Opening hours / meal times
        <input
          name="opening_hours"
          defaultValue={existing?.opening_hours ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
          placeholder="e.g. 10:00–14:00"
        />
      </label>
      <label className="block text-sm">
        Eligibility requirements
        <textarea
          name="eligibility"
          defaultValue={existing?.eligibility ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
          rows={2}
        />
      </label>
      <label className="block text-sm">
        Referral requirements
        <textarea
          name="referral_requirements"
          defaultValue={existing?.referral_requirements ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
          rows={2}
        />
      </label>
      <label className="block text-sm">
        Contact
        <input
          name="contact"
          defaultValue={existing?.contact ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Service instructions
        <textarea
          name="service_instructions"
          defaultValue={existing?.service_instructions ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
          rows={2}
        />
      </label>
      {category === "clothing_bank" ? (
        <label className="block text-sm">
          Clothing service type
          <select
            name="clothing_service_type"
            defaultValue={existing?.clothing_service_type ?? ""}
            className="mt-1 w-full rounded border px-3 py-2"
          >
            <option value="">Not specified</option>
            <option value="provides_clothing">Provides clothing to people in need</option>
            <option value="accepts_donations">Accepts clothing donations</option>
            <option value="both">Provides clothing and accepts donations</option>
          </select>
        </label>
      ) : null}
      <label className="block text-sm">
        Information source
        <input
          name="information_source"
          defaultValue={existing?.information_source ?? ""}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input name="is_published" type="checkbox" defaultChecked={existing?.is_published ?? false} />
        Publish to tenant directory (still requires verification for trust badge)
      </label>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
      >
        {pending ? "Saving…" : existing ? "Save changes" : "Create listing"}
      </button>
    </form>
  );
}
