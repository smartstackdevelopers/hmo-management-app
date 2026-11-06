import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchWaitingList } from "@/lib/housingApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function WaitingListPage() {
  const session = await requireAuthenticatedSession("/dashboard/waiting-list");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["waiting_list.manage", "waiting_list.read"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load waiting list." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const page = await fetchWaitingList({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F2.5"
          title="Housing waiting list"
          description="Organisation FIFO positions with optional priority labels. Position does not guarantee allocation."
        />
        <Link
          href="/dashboard/housing-applications"
          className="inline-block rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          Applications
        </Link>
        {page.items.length === 0 ? (
          <EmptyState
            title="Waiting list empty"
            description="Approved applications can be added from the application detail page."
          />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((row) => (
              <li key={row.id} className="p-4 text-sm">
                <p className="font-medium text-forest-900">
                  #{row.position} · {row.application_reference ?? row.application_id}
                </p>
                <p className="text-slate-600">
                  {row.status} · priority {row.priority} · application {row.application_status}
                </p>
                <Link
                  href={`/dashboard/housing-applications/${row.application_id}`}
                  className="text-teal-800 hover:underline"
                >
                  Open application
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load waiting list."}
      />
    );
  }
}
