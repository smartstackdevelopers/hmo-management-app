import Link from "next/link";
import { redirect } from "next/navigation";
import {
  AuthAlert,
  AuthShell,
  authInputClass,
  authLabelClass,
  authPrimaryButtonClass,
} from "@/components/auth/AuthShell";
import { friendlyAuthError } from "@/lib/authErrors";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const PUBLIC_ROLES = [
  { value: "tenant", label: "Tenant", hint: "I live in a home managed on HMore" },
  { value: "landlord", label: "Landlord", hint: "I own or manage properties" },
  { value: "support_worker", label: "Support Worker", hint: "I support tenants" },
  { value: "maintenance_contractor", label: "Maintenance Contractor", hint: "I carry out repairs" },
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
    const message = friendlyAuthError(text || String(response.status), "register") ?? "";
    redirect(`/register?error=${encodeURIComponent(message)}`);
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
    <AuthShell
      headline="Request access to HMore."
      subline="Tell us who you are. Your housing provider reviews every request before access is granted."
    >
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Request access</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Your account stays pending until an administrator approves it. Admin roles are assigned by your organisation.
        </p>
      </header>
      {params.error ? (
        <div className="mt-6">
          <AuthAlert message={params.error.slice(0, 200)} />
        </div>
      ) : null}
      <form action={registerAction} className="mt-6 space-y-5">
        <fieldset>
          <legend className={authLabelClass}>I am a…</legend>
          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {PUBLIC_ROLES.map((role, index) => (
              <label
                key={role.value}
                className="flex cursor-pointer gap-3 rounded-xl border border-slate-200 bg-white p-3 text-sm hover:border-brand-300 has-[:checked]:border-brand-600 has-[:checked]:bg-brand-50 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-600"
              >
                <input
                  type="radio"
                  name="requested_role"
                  value={role.value}
                  required
                  defaultChecked={index === 0}
                  className="mt-0.5 h-4 w-4 accent-brand-700"
                />
                <span>
                  <span className="block font-semibold text-slate-900">{role.label}</span>
                  <span className="block text-xs text-slate-500">{role.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <label className={authLabelClass}>
          Full name
          <input name="full_name" required autoComplete="name" className={authInputClass} />
        </label>
        <div className="grid gap-5 sm:grid-cols-2">
          <label className={authLabelClass}>
            Email
            <input name="email" type="email" required autoComplete="email" className={authInputClass} />
          </label>
          <label className={authLabelClass}>
            Phone <span className="font-normal text-slate-400">(optional)</span>
            <input name="phone" type="tel" autoComplete="tel" className={authInputClass} />
          </label>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <label className={authLabelClass}>
            Password
            <input
              name="password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              aria-describedby="password-hint"
              className={authInputClass}
            />
          </label>
          <label className={authLabelClass}>
            Confirm password
            <input
              name="confirm_password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              className={authInputClass}
            />
          </label>
        </div>
        <p id="password-hint" className="-mt-3 text-xs text-slate-500">
          At least 8 characters.
        </p>
        <details className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
          <summary className="cursor-pointer font-medium text-slate-700">I have an organisation or invitation code</summary>
          <div className="mt-4 space-y-4">
            <label className={authLabelClass}>
              Organisation code
              <input name="organisation_slug" placeholder="e.g. demo-housing" className={authInputClass} />
            </label>
            <label className={authLabelClass}>
              Invitation code
              <input name="invitation_code" className={authInputClass} />
            </label>
          </div>
        </details>
        <div className="space-y-2 text-sm text-slate-700">
          <label className="flex items-start gap-2.5">
            <input name="terms_accepted" type="checkbox" required className="mt-0.5 h-4 w-4 accent-brand-700" />
            I accept the terms of use
          </label>
          <label className="flex items-start gap-2.5">
            <input name="privacy_accepted" type="checkbox" required className="mt-0.5 h-4 w-4 accent-brand-700" />
            I accept the privacy notice
          </label>
        </div>
        <button type="submit" className={authPrimaryButtonClass}>
          Send request
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        Already approved?{" "}
        <Link className="font-semibold text-brand-700 hover:underline" href="/login">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
