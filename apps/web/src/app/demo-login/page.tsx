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
      <main className="mx-auto max-w-lg p-8">
        <h1 className="text-2xl font-semibold">Demo login disabled</h1>
        <p className="mt-2 text-slate-600">
          Set <code>NEXT_PUBLIC_DEMO_AUTH=1</code> in <code>apps/web/.env.local</code> and{" "}
          <code>HMORE_DEMO_AUTH=true</code> on the API (development only).
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-lg space-y-6 p-8">
      <header>
        <p className="text-sm font-medium uppercase tracking-wide text-amber-700">Local meeting only</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Dummy role login</h1>
        <p className="mt-2 text-slate-600">
          Pick a role to sign in without Auth0. Uses FastAPI demo tokens against PostgreSQL. Do not enable in
          production.
        </p>
      </header>
      <div className="grid gap-3">
        {ROLES.map((item) => (
          <form key={item.role} action={demoLoginAction}>
            <input type="hidden" name="role" value={item.role} />
            <button
              type="submit"
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-left text-base font-semibold text-slate-900 shadow-sm hover:border-teal-600 hover:bg-teal-50"
            >
              {item.label}
            </button>
          </form>
        ))}
      </div>
      <p className="text-sm text-slate-500">
        Real Auth0 login remains at <a className="underline" href="/auth/login">/auth/login</a>.
      </p>
    </main>
  );
}
