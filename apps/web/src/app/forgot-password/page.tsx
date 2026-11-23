import Link from "next/link";
import { redirect } from "next/navigation";
import {
  AuthShell,
  authInputClass,
  authLabelClass,
  authLinkClass,
  authPrimaryButtonClass,
} from "@/components/auth/AuthShell";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function forgotAction(formData: FormData) {
  "use server";
  const email = String(formData.get("email") || "");
  try {
    await fetch(`${API_BASE}/api/v1/auth/password/forgot`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email }),
      cache: "no-store",
    });
  } catch {
    // Same confirmation either way, so the page never reveals whether an account exists.
  }
  redirect("/forgot-password?sent=1");
}

export default async function ForgotPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ sent?: string }>;
}) {
  const params = await searchParams;
  const sent = params.sent === "1";
  return (
    <AuthShell>
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">Reset password</h1>
      <p className="mt-1.5 text-sm text-slate-600">Enter your email and we’ll send you a secure reset link.</p>
      {sent ? (
        <p role="status" className="mt-5 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          If that email has an HMore account, a reset link is on its way.
        </p>
      ) : (
        <form action={forgotAction} className="mt-5 space-y-4">
          <label className={authLabelClass}>
            Email
            <input
              name="email"
              type="email"
              required
              autoComplete="email"
              placeholder="name@organisation.org.uk"
              className={authInputClass}
            />
          </label>
          <div className="pt-1">
            <button type="submit" className={authPrimaryButtonClass}>
              Send reset link
            </button>
          </div>
        </form>
      )}
      <p className="mt-5 text-center text-xs">
        <Link className={authLinkClass} href="/login">
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
}
