"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui/primitives";
import { createOrganisation } from "@/lib/organisationsApi";
import type { GovAuth } from "@/lib/platformGovernanceApi";

type Props = {
  auth: GovAuth;
};

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
}

export function CreateOrganisationForm({ auth }: Props) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [status, setStatus] = useState<"idle" | "saving" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  function onNameChange(value: string) {
    setName(value);
    if (!slugTouched) {
      setSlug(slugify(value));
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmedName = name.trim();
    const trimmedSlug = slug.trim() || slugify(trimmedName);
    if (!trimmedName || !trimmedSlug) {
      setMessage("Name and slug are required.");
      setStatus("error");
      return;
    }
    setStatus("saving");
    setMessage(null);
    try {
      await createOrganisation(auth, { name: trimmedName, slug: trimmedSlug });
      setName("");
      setSlug("");
      setSlugTouched(false);
      setStatus("idle");
      router.refresh();
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Could not create organisation.");
    }
  }

  return (
    <form
      id="create-organisation"
      onSubmit={onSubmit}
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
      aria-labelledby="create-org-heading"
    >
      <h2 id="create-org-heading" className="text-base font-semibold text-slate-900">
        New organisation
      </h2>
      <p className="mt-1 text-sm text-slate-500">The organisation is saved to your platform directory.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          <span className={labelClass}>Name</span>
          <input
            className={`mt-1 ${inputClass}`}
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            required
            maxLength={255}
            autoComplete="organization"
          />
        </label>
        <label className="block text-sm">
          <span className={labelClass}>Slug</span>
          <input
            className={`mt-1 font-mono ${inputClass}`}
            value={slug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value);
            }}
            required
            maxLength={100}
            pattern="[a-z0-9-]+"
            title="Lowercase letters, numbers, and hyphens"
          />
        </label>
      </div>
      {message ? (
        <p className="mt-3 text-sm text-red-700" role="alert">
          {message}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={status === "saving"}
        className={`${btnPrimary} mt-4`}
      >
        {status === "saving" ? "Creating…" : "Create organisation"}
      </button>
    </form>
  );
}