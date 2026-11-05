import Link from "next/link";

export default function NewTenantPage() {
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-3xl font-semibold text-forest-900">Create tenant</h1>
      <p className="text-slate-700">
        Submit tenant records through{" "}
        <code className="rounded bg-slate-100 px-1">POST /api/v1/tenants</code>. Required field:
        preferred name. Optional: contact, consent, preferences, needs/goals, tenancy reference.
      </p>
      <form className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
        <label className="block text-sm">
          Preferred name
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            name="preferred_name"
            required
            disabled
            placeholder="Requires authenticated API client"
          />
        </label>
        <p className="text-sm text-slate-500">
          Interactive authenticated forms wire to the API once the Auth0 session exposes an access
          token to the browser client (F1.9 dashboards).
        </p>
      </form>
      <Link className="text-sm text-teal-800 hover:underline" href="/tenants">
        Back to tenants
      </Link>
    </div>
  );
}
