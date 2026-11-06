import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchIncidents } from "@/lib/incidentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function IncidentsPage() {
  const session = await requireAuthenticatedSession("/dashboard/incidents");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "incidents.manage",
      "incidents.read.assigned",
      "incidents.create.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load incidents." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const page = await fetchIncidents({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F2.4"
          title="Incident reports"
          description="Record and track operational incidents. Categories are organisation-defined."
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link href="/dashboard/incidents/new" className="rounded-md bg-teal-700 px-3 py-2 text-white">
            New incident
          </Link>
          <Link href="/dashboard/workload" className="rounded-md border border-slate-300 px-3 py-2">
            Workload
          </Link>
        </div>
        {page.items.length === 0 ? (
          <EmptyState title="No incidents" description="Create an incident report to get started." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((row) => (
              <li key={row.id} className="p-4 text-sm">
                <Link href={`/dashboard/incidents/${row.id}`} className="font-medium text-forest-900 hover:underline">
                  {row.reference_number} · {row.title}
                </Link>
                <p className="text-slate-600">
                  {row.status} · {row.severity} · {row.category} · follow-ups open:{" "}
                  {row.open_follow_up_count}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load incidents."} />
    );
  }
}
