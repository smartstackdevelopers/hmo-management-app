import Link from "next/link";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import {
  AuthAlert,
  AuthShell,
  authInputClass,
  authLabelClass,
  authPrimaryButtonClass,
} from "@/components/auth/AuthShell";
import { friendlyAuthError } from "@/lib/authErrors";
import { homePathForRole } from "@/lib/dashboardAccess";
import { cookieOptions, NATIVE_ACCESS_COOKIE, NATIVE_REFRESH_COOKIE } from "@/lib/nativeAuth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function loginAction(formData: FormData) {
  "use server";
  const email = String(formData.get("email") || "");
  const password = String(formData.get("password") || "");
  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    const message = friendlyAuthError(text || String(response.status), "login") ?? "";
    redirect(`/login?error=${encodeURIComponent(message)}`);
  }
  const payload = (await response.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  };
  const jar = await cookies();
  jar.set(NATIVE_ACCESS_COOKIE, payload.access_token, cookieOptions(payload.expires_in || 900));
  jar.set(NATIVE_REFRESH_COOKIE, payload.refresh_token, cookieOptions(60 * 60 * 24 * 14));

  const me = await fetch(`${API_BASE}/api/v1/rbac/me`, {
    headers: { Authorization: `Bearer ${payload.access_token}`, Accept: "application/json" },
    cache: "no-store",
  });
  if (me.ok) {
    const rbac = (await me.json()) as { active_role?: string };
    redirect(homePathForRole(rbac.active_role ?? null));
  }
  redirect("/dashboard");
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; returnTo?: string }>;
}) {
  const params = await searchParams;
  const showDemo = process.env.NODE_ENV !== "production";
  return (
    <AuthShell>
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Sign in</h1>
        <p className="mt-2 text-sm text-slate-600">Use your approved HMore email and password.</p>
      </header>
      {params.error ? (
        <div className="mt-6">
          <AuthAlert message={params.error.slice(0, 200)} />
        </div>
      ) : null}
      <form action={loginAction} className="mt-6 space-y-5">
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
        <label className={authLabelClass}>
          Password
          <input
            name="password"
            type="password"
            required
            autoComplete="current-password"
            className={authInputClass}
          />
        </label>
        <button type="submit" className={authPrimaryButtonClass}>
          Sign in
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        New to HMore?{" "}
        <Link className="font-semibold text-brand-700 hover:underline" href="/register">
          Request access
        </Link>
      </p>
      {showDemo ? (
        <div className="mt-10 rounded-xl border border-dashed border-slate-300 bg-white/60 px-4 py-3 text-center text-xs text-slate-500">
          Local development only ·{" "}
          <Link className="font-semibold text-slate-700 hover:underline" href="/demo-login">
            Demo accounts
          </Link>
        </div>
      ) : null}
    </AuthShell>
  );
}
