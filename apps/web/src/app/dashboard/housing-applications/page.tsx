import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchApplications } from "@/lib/housingApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function HousingApplicationsPage({
  searchParams,
}: {
  searchParams?: Promise<{ view?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/housing-applications");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "applications.manage",
      "applications.review",
      "applications.read.own",
      "applications.read.assigned",
      "applications.create.own",
      "applications.create.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load applications." />;
  }
  const params = searchParams ? await searchParams : {};
  const pending = params.view === "pending";
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const page = await fetchApplications({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      pendingApprovals: pending,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F2.5"
          title="Housing applications"
          description="Organisation-scoped applications and approvals. Waiting-list position does not guarantee allocation."
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link
            href="/dashboard/housing-applications/new"
            className="rounded-md bg-teal-700 px-3 py-2 text-white"
          >
            New application
          </Link>
          <Link href="/dashboard/housing-applications" className="rounded-md border border-slate-300 px-3 py-2">
            All
          </Link>
          <Link
            href="/dashboard/housing-applications?view=pending"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Pending approvals
          </Link>
          <Link href="/dashboard/waiting-list" className="rounded-md border border-slate-300 px-3 py-2">
            Waiting list
          </Link>
        </div>
        {page.items.length === 0 ? (
          <EmptyState title="No applications" description="Create a housing application to begin." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((row) => (
              <li key={row.id} className="p-4 text-sm">
                <Link
                  href={`/dashboard/housing-applications/${row.id}`}
                  className="font-medium text-forest-900 hover:underline"
                >
                  {row.reference_number} · {row.status}
                </Link>
                <p className="text-slate-600">
                  Priority {row.priority}
                  {row.on_waiting_list ? ` · waiting list #${row.waiting_list_position}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load applications."}
      />
    );
  }
}
