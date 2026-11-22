import Link from "next/link";
import { redirect } from "next/navigation";
import {
  AuthAlert,
  AuthShell,
  authInputClass,
  authLabelClass,
  authLinkClass,
  authPrimaryButtonClass,
} from "@/components/auth/AuthShell";
import { friendlyAuthError } from "@/lib/authErrors";

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
    const message = friendlyAuthError(text || String(response.status), "register") ?? "";
    redirect(`/register?error=${encodeURIComponent(message)}`);
  }
  redirect("/register/pending");
}

const checkboxClass = "h-4 w-4 rounded accent-brand-700";

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const params = await searchParams;
  return (
    <AuthShell
      headline="Join your organisation on HMore."
      subline="Every account is reviewed by an administrator before access is granted."
      points={["Choose your role", "Admin approval", "Secure from day one"]}
    >
      <header className="-mt-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Request access</h1>
        <p className="mt-1.5 text-sm text-slate-600">Tell us who you are. Admin roles cannot be self-requested.</p>
      </header>
      {params.error ? (
        <div className="mt-5">
          <AuthAlert message={params.error.slice(0, 200)} />
        </div>
      ) : null}
      <form action={registerAction} className="mt-5 space-y-4">
        <label className={authLabelClass}>
          Full name
          <input name="full_name" required autoComplete="name" className={authInputClass} />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className={authLabelClass}>
            Email
            <input name="email" type="email" required autoComplete="email" className={authInputClass} />
          </label>
          <label className={authLabelClass}>
            Phone (optional)
            <input name="phone" type="tel" autoComplete="tel" placeholder="07700 900456" className={authInputClass} />
          </label>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className={authLabelClass}>
            Password
            <input
              name="password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              title="At least 8 characters"
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
        <div className="grid gap-4 sm:grid-cols-2">
          <label className={authLabelClass}>
            Role
            <select name="requested_role" required defaultValue="tenant" className={authInputClass}>
              {PUBLIC_ROLES.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </label>
          <label className={authLabelClass}>
            Organisation code
            <input name="organisation_slug" placeholder="e.g. demo-housing" className={authInputClass} />
          </label>
        </div>
        <input type="hidden" name="invitation_code" value="" />
        <div className="space-y-2.5 pt-1 text-xs text-slate-600">
          <label className="flex items-center gap-2.5">
            <input name="terms_accepted" type="checkbox" required className={checkboxClass} />
            I accept the terms of use
          </label>
          <label className="flex items-center gap-2.5">
            <input name="privacy_accepted" type="checkbox" required className={checkboxClass} />
            I accept the privacy notice
          </label>
        </div>
        <div className="pt-1">
          <button type="submit" className={authPrimaryButtonClass}>
            Submit request
          </button>
        </div>
      </form>
      <p className="mt-5 text-center text-xs">
        <Link className={authLinkClass} href="/login">
          Already registered? Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
