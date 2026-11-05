import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { requireDashboardRole } from "@/lib/session";

export default async function SuperAdminDashboardPage() {
  const session = await requireDashboardRole("super_admin", "/dashboard/super-admin");

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Auth0 not configured"
        description="Super Admin shell requires Auth0 environment variables."
      />
    );
  }

  if (!session.authorization) {
    return (
      <ErrorState description="Authorization snapshot unavailable. Confirm API connectivity and membership." />
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        eyebrow="Platform"
        title="Super Admin home"
        description="Platform-level shell for organisation administration and monitoring. Live platform metrics are not part of F1.9."
      />

      <section aria-labelledby="sa-nav-heading" className="grid gap-4 sm:grid-cols-2">
        <h2 id="sa-nav-heading" className="sr-only">
          Platform navigation
        </h2>
        <Link
          href="/dashboard/super-admin/organisations"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Organisations</h3>
          <p className="mt-2 text-sm text-slate-600">
            Open the organisations administration entry. Creation uses the existing API when
            available.
          </p>
        </Link>
        <Link
          href="/dashboard/audit"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Audit logs</h3>
          <p className="mt-2 text-sm text-slate-600">
            Platform audit access requires audit_logs.read and API organisation or platform context.
          </p>
        </Link>
        <Link
          href="/account"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Account</h3>
          <p className="mt-2 text-sm text-slate-600">Auth0 profile and logout.</p>
        </Link>
        <Link
          href="/health"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Service status</h3>
          <p className="mt-2 text-sm text-slate-600">Local process health for the web app.</p>
        </Link>
      </section>

      <EmptyState
        title="No live platform statistics"
        description="Operational metrics, billing, and AI cost dashboards arrive in later phases."
        hint="This empty state is intentional — values are not invented."
      />
    </div>
  );
}
