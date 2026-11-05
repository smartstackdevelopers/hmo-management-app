import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { requireDashboardRole } from "@/lib/session";

export default async function OrganisationAdminDashboardPage() {
  const session = await requireDashboardRole(
    "organisation_admin",
    "/dashboard/organisation-admin",
  );

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Auth0 not configured"
        description="Organisation Admin shell requires Auth0 environment variables."
      />
    );
  }

  if (!session.authorization) {
    return (
      <ErrorState description="Authorization snapshot unavailable. Confirm API connectivity and membership." />
    );
  }

  const orgId = session.authorization.active_organisation_id;

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        eyebrow="Organisation"
        title="Organisation Admin home"
        description="Organisation-scoped shell. Context below comes from the API authorization snapshot, not browser storage."
      />

      <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm">
        <p className="font-medium text-slate-500">Trusted organisation context</p>
        <p className="mt-2 break-all font-mono text-forest-900">
          {orgId ?? "No organisation id on active membership — send X-Organisation-Id only for an assigned org via API clients."}
        </p>
      </div>

      <section aria-labelledby="oa-nav-heading" className="grid gap-4 sm:grid-cols-2">
        <h2 id="oa-nav-heading" className="sr-only">
          Organisation navigation
        </h2>
        <Link
          href="/tenants"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Tenants</h3>
          <p className="mt-2 text-sm text-slate-600">Requires tenants.read on the API.</p>
        </Link>
        <Link
          href="/properties"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Properties</h3>
          <p className="mt-2 text-sm text-slate-600">Requires properties.read on the API.</p>
        </Link>
        <Link
          href="/rooms"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Rooms</h3>
          <p className="mt-2 text-sm text-slate-600">Requires rooms.read on the API.</p>
        </Link>
        <Link
          href="/dashboard/files"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Private files</h3>
          <p className="mt-2 text-sm text-slate-600">Requires files.read (F1.8).</p>
        </Link>
        <Link
          href="/dashboard/audit"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Audit logs</h3>
          <p className="mt-2 text-sm text-slate-600">Requires audit_logs.read.</p>
        </Link>
      </section>

      <EmptyState
        title="No invented organisation KPIs"
        description="Occupancy, support caseloads, and AI cost widgets are later phases. This home is a shell only."
      />
    </div>
  );
}
