import Link from "next/link";
import { redirect } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const PUBLIC_ROLES = [
  { value: "tenant", label: "Tenant" },
  { value: "landlord", label: "Landlord" },
  { value: "support_worker", label: "Support Worker" },
  { value: "maintenance_contractor", label: "Maintenance Contractor" },
] as const;

async function registerAction(formData: FormData) {
  "use server";
  const body = {
    full_name: String(formData.get("full_name") || ""),
    email: String(formData.get("email") || ""),
    phone: String(formData.get("phone") || "") || null,
    password: String(formData.get("password") || ""),
    confirm_password: String(formData.get("confirm_password") || ""),
    requested_role: String(formData.get("requested_role") || ""),
    organisation_slug: String(formData.get("organisation_slug") || "") || null,
    invitation_code: String(formData.get("invitation_code") || "") || null,
    terms_accepted: formData.get("terms_accepted") === "on",
    privacy_accepted: formData.get("privacy_accepted") === "on",
  };
  const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    redirect(`/register?error=${encodeURIComponent(text.slice(0, 200) || "Registration failed")}`);
  }
  redirect("/register/pending");
}

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const params = await searchParams;
  return (
    <main className="mx-auto max-w-lg space-y-6 p-8">
      <header>
        <p className="text-sm font-medium uppercase tracking-wide text-teal-700">HMore registration</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Request access</h1>
        <p className="mt-2 text-slate-600">
          Accounts stay pending until an Organisation Admin or Super Admin approves your request. You cannot
          self-register as Super Admin or Organisation Admin.
        </p>
      </header>
      {params.error ? (
        <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{params.error}</p>
      ) : null}
      <form action={registerAction} className="space-y-3">
        <label className="block text-sm font-medium">
          Full name
          <input name="full_name" required className="mt-1 w-full rounded border px-3 py-2" />
        </label>
        <label className="block text-sm font-medium">
          Email
          <input name="email" type="email" required className="mt-1 w-full rounded border px-3 py-2" />
        </label>
        <label className="block text-sm font-medium">
          Phone
          <input name="phone" className="mt-1 w-full rounded border px-3 py-2" />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input name="password" type="password" required minLength={8} className="mt-1 w-full rounded border px-3 py-2" />
        </label>
        <label className="block text-sm font-medium">
          Confirm password
          <input
            name="confirm_password"
            type="password"
            required
            minLength={8}
            className="mt-1 w-full rounded border px-3 py-2"
          />
        </label>
        <label className="block text-sm font-medium">
          Requested role
          <select name="requested_role" required className="mt-1 w-full rounded border px-3 py-2">
            {PUBLIC_ROLES.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium">
          Organisation slug (optional)
          <input name="organisation_slug" placeholder="demo-housing" className="mt-1 w-full rounded border px-3 py-2" />
        </label>
        <label className="block text-sm font-medium">
          Invitation code (optional)
          <input name="invitation_code" className="mt-1 w-full rounded border px-3 py-2" />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input name="terms_accepted" type="checkbox" required /> I accept the terms of use
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input name="privacy_accepted" type="checkbox" required /> I accept the privacy notice
        </label>
        <button type="submit" className="w-full rounded bg-teal-700 px-4 py-3 font-semibold text-white">
          Submit registration
        </button>
      </form>
      <p className="text-sm text-slate-600">
        Already registered? <Link className="underline" href="/login">Sign in</Link>
      </p>
    </main>
  );
}
