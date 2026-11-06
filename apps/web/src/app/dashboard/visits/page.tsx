import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchVisits } from "@/lib/opsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function VisitsPage() {
  const session = await requireAuthenticatedSession("/dashboard/visits");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["visits.manage.assigned", "tenants.manage"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load visits." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const page = await fetchVisits({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      upcomingOnly: true,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader eyebrow="F2.2" title="Tenant visits" description="Upcoming scheduled and confirmed visits." />
        <Link href="/dashboard/visits/new" className="inline-flex rounded-md bg-teal-700 px-3 py-2 text-sm text-white">
          Schedule visit
        </Link>
        {page.items.length === 0 ? (
          <EmptyState title="No upcoming visits" description="Schedule a visit for an assigned tenant." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((visit) => (
              <li key={visit.id} className="p-4 text-sm">
                <p className="font-medium text-forest-900">{visit.purpose}</p>
                <p className="text-slate-600">
                  {new Date(visit.scheduled_at).toLocaleString()} · {visit.status}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return <ErrorState description={error instanceof Error ? error.message : "Failed to load visits."} />;
  }
}
