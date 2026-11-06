import Link from "next/link";
import { redirect } from "next/navigation";
import { SafeguardingActions } from "@/components/compliance/SafeguardingActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchSafeguardingReminders } from "@/lib/complianceApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function SafeguardingPage({
  searchParams,
}: {
  searchParams?: Promise<{ view?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/safeguarding");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "safeguarding.reminders.manage",
      "safeguarding.reminders.manage.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load reminders." />;
  }
  const params = searchParams ? await searchParams : {};
  const overdueOnly = params.view === "overdue";
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const page = await fetchSafeguardingReminders({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      overdueOnly,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F2.3"
          title="Safeguarding reminders"
          description="Follow-up tracking only — not a case-management system. Notification content stays non-sensitive."
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link
            href="/dashboard/safeguarding/new"
            className="rounded-md bg-teal-700 px-3 py-2 text-white"
          >
            New reminder
          </Link>
          <Link href="/dashboard/safeguarding" className="rounded-md border border-slate-300 px-3 py-2">
            All
          </Link>
          <Link
            href="/dashboard/safeguarding?view=overdue"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Overdue
          </Link>
          <Link href="/dashboard/training" className="rounded-md border border-slate-300 px-3 py-2">
            Training
          </Link>
        </div>
        {page.items.length === 0 ? (
          <EmptyState title="No reminders" description="Create a safeguarding follow-up reminder." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((row) => (
              <li key={row.id} className="p-4 text-sm">
                <p className="font-medium text-forest-900">{row.title}</p>
                <p className="text-slate-600">
                  {row.status} · {row.priority} · due {new Date(row.due_at).toLocaleString()}
                </p>
                <SafeguardingActions
                  reminderId={row.id}
                  status={row.status}
                  accessToken={token}
                  organisationId={orgId}
                  role={session.authorization?.active_role}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load safeguarding reminders."}
      />
    );
  }
}
