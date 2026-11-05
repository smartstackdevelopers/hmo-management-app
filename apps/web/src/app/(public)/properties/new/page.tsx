import Link from "next/link";

export default function NewPropertyPage() {
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-3xl font-semibold text-forest-900">Create property</h1>
      <p className="text-slate-700">
        API: <code className="rounded bg-slate-100 px-1">POST /api/v1/properties</code>. Required:
        name, address line 1, city, postcode.
      </p>
      <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-600">
        Authenticated create form lands with F1.9 role dashboards. Validation and organisation
        stamping are enforced by FastAPI.
      </div>
      <Link className="text-sm text-teal-800 hover:underline" href="/properties">
        Back to properties
      </Link>
    </div>
  );
}
