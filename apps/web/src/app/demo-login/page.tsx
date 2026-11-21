import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { DEMO_LOGIN_COOKIE, isWebDemoAuthEnabled } from "@/lib/demoAuth";
import { homePathForRole } from "@/lib/dashboardAccess";

const ROLES = [
  { role: "super_admin", label: "Super Admin" },
  { role: "organisation_admin", label: "Organisation Admin" },
  { role: "landlord", label: "Landlord" },
  { role: "tenant", label: "Tenant" },
  { role: "support_worker", label: "Support Worker" },
  { role: "maintenance_contractor", label: "Maintenance Contractor" },
] as const;

async function demoLoginAction(formData: FormData) {
  "use server";
  if (!isWebDemoAuthEnabled()) {
    throw new Error("Demo auth disabled");
  }
  const role = String(formData.get("role") || "");
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${apiBase}/api/v1/auth/demo/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ role }),
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Demo login failed (${response.status})`);
  }
  const payload = (await response.json()) as { access_token: string; role: string };
  const jar = await cookies();
  jar.set(DEMO_LOGIN_COOKIE, payload.access_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  redirect(homePathForRole(payload.role));
}

export default async function DemoLoginPage() {
  if (!isWebDemoAuthEnabled()) {
    return (
      <main className="min-h-screen bg-cream px-6 py-16">
        <div className="mx-auto max-w-lg rounded-2xl border border-slate-200 bg-white p-8 shadow-card">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">Local development only</p>
          <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-navy-900">Demo login disabled</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Set <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">NEXT_PUBLIC_DEMO_AUTH=1</code> in{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">apps/web/.env.local</code> and{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">HMORE_DEMO_AUTH=true</code> on the API
            (development only).
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-cream px-6 py-16">
      <div className="mx-auto max-w-lg space-y-6">
        <div
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800"
          role="note"
        >
          Local development only — never enable demo login in production.
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-card">
          <header>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">Demo sign-in</p>
            <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-navy-900">Choose a role</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Sign in as a sample user for local testing. This uses demo accounts on your local database.
            </p>
          </header>
          <div className="mt-6 grid gap-3">
            {ROLES.map((item) => (
              <form key={item.role} action={demoLoginAction}>
                <input type="hidden" name="role" value={item.role} />
                <button
                  type="submit"
                  className="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-semibold text-slate-900 transition hover:border-brand-200 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                >
                  <span
                    aria-hidden="true"
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700"
                  >
                    {item.label
                      .split(" ")
                      .map((word) => word[0])
                      .join("")
                      .slice(0, 2)}
                  </span>
                  {item.label}
                </button>
              </form>
            ))}
          </div>
          <p className="mt-6 text-sm text-slate-500">
            Use the{" "}
            <a className="font-semibold text-brand-700 hover:underline" href="/auth/login">
              normal sign-in page
            </a>{" "}
            for real accounts.
          </p>
        </div>
      </div>
    </main>
  );
}
