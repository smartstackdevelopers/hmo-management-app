import Link from "next/link";

export default function TenantsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-forest-900">Tenants</h1>
        <p className="mt-2 text-slate-700">
          Organisation-scoped tenant person records (F1.6). Access requires Auth0 and
          <code className="mx-1 rounded bg-slate-100 px-1">tenants.read</code>
          permission. Backend isolation is mandatory.
        </p>
      </div>
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
        <p>No client-side list is loaded without a live access token.</p>
        <p className="mt-2 text-sm">
          Use <code className="rounded bg-slate-100 px-1">GET /api/v1/tenants</code> with
          organisation context headers after sign-in.
        </p>
      </div>
      <div className="flex gap-3">
        <Link className="rounded-md bg-teal-700 px-4 py-2 text-sm text-white" href="/tenants/new">
          New tenant
        </Link>
        <Link className="rounded-md px-4 py-2 text-sm text-forest-900 hover:bg-slate-100" href="/">
          Home
        </Link>
      </div>
    </div>
  );
}
