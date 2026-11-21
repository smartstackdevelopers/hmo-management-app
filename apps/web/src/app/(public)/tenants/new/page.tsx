import Link from "next/link";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { inputClass, labelClass, linkClass } from "@/components/ui/primitives";

export default function NewTenantPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link className={`text-sm ${linkClass}`} href="/tenants">
        ← Back to tenants
      </Link>
      <PageHeader
        eyebrow="People"
        title="Create tenant"
        description="Submit tenant records through POST /api/v1/tenants. Required: preferred name. Optional: contact, consent, preferences, needs and goals, tenancy reference."
      />
      <form className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
        <div>
          <label htmlFor="preferred_name" className={labelClass}>
            Preferred name
          </label>
          <input
            id="preferred_name"
            className={`mt-1.5 ${inputClass}`}
            name="preferred_name"
            required
            disabled
            placeholder="Requires authenticated API client"
          />
        </div>
        <p className="text-sm text-slate-500">
          Interactive authenticated forms wire to the API once the session exposes an access token to the browser client.
        </p>
      </form>
    </div>
  );
}
