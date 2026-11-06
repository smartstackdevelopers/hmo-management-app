import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { fetchHandovers } from "@/lib/supportApi";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function HandoversPage() {
  const session = await requireAuthenticatedSession("/dashboard/handovers");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "support_notes.read.assigned",
      "tenants.manage",
      "tenants.read",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load handovers." />;
  }

  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) {
      return <ErrorState description="Access token unavailable." />;
    }
    const page = await fetchHandovers({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      pendingOnly: true,
    });

    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="Support"
          title="Handovers"
          description="Pending and in-progress handovers for your assigned cases."
        />
        <Link
          href="/dashboard/handovers/new"
          className="inline-flex rounded-md bg-teal-700 px-3 py-2 text-sm text-white"
        >
          New handover
        </Link>
        {page.items.length === 0 ? (
          <EmptyState title="No pending handovers" description="Submitted or acknowledged handovers will appear here." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-medium text-forest-900">{item.summary}</p>
                  <p className="text-xs text-slate-500">
                    {item.status} · {item.priority}
                  </p>
                </div>
                <Link href={`/dashboard/handovers/${item.id}`} className="text-sm text-teal-800 underline">
                  Open
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load handovers."} />
    );
  }
}
