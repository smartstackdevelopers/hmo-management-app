import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { requireDashboardRole } from "@/lib/session";

export default async function LandlordDashboardPage() {
  const session = await requireDashboardRole("landlord", "/dashboard/landlord");

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Auth0 not configured"
        description="Landlord shell requires Auth0 environment variables."
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
        eyebrow="Landlord"
        title="Landlord home"
        description="Property-focused shell. Property records are not invented here — use the properties API when available."
      />

      <section aria-labelledby="ll-nav-heading" className="grid gap-4 sm:grid-cols-2">
        <h2 id="ll-nav-heading" className="sr-only">
          Landlord navigation
        </h2>
        <Link
          href="/properties"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Properties</h3>
          <p className="mt-2 text-sm text-slate-600">
            API enforces ownership rules for properties.manage.
          </p>
        </Link>
        <Link
          href="/rooms"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Rooms</h3>
          <p className="mt-2 text-sm text-slate-600">Room baseline records from F1.6.</p>
        </Link>
        <Link
          href="/account"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
        >
          <h3 className="font-semibold text-forest-900">Account</h3>
          <p className="mt-2 text-sm text-slate-600">Profile and logout via Auth0.</p>
        </Link>
      </section>

      <EmptyState
        title="No property data loaded"
        description="This shell does not fabricate occupancy or rent figures. Connect a live token and call GET /api/v1/properties to populate later UI."
      />
    </div>
  );
}
