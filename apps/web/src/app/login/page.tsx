import Link from "next/link";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
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
    redirect(`/login?error=${encodeURIComponent(text.slice(0, 180) || "Login failed")}`);
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
  return (
    <main className="mx-auto max-w-md space-y-6 p-8">
      <header>
        <p className="text-sm font-medium uppercase tracking-wide text-teal-700">HMore native login</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Sign in</h1>
        <p className="mt-2 text-slate-600">Use your approved HMore email and password. Pending accounts cannot access the app.</p>
      </header>
      {params.error ? (
        <p className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{params.error}</p>
      ) : null}
      <form action={loginAction} className="space-y-4">
        <label className="block text-sm font-medium text-slate-700">
          Email
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Password
          <input
            name="password"
            type="password"
            required
            autoComplete="current-password"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
          />
        </label>
        <button
          type="submit"
          className="w-full rounded bg-teal-700 px-4 py-3 font-semibold text-white hover:bg-teal-800"
        >
          Sign in
        </button>
      </form>
      <p className="text-sm text-slate-600">
        Need an account? <Link className="underline" href="/register">Register</Link>
        {" · "}
        <Link className="underline" href="/demo-login">Meeting demo login</Link>
      </p>
    </main>
  );
}
