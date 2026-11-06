import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchShifts } from "@/lib/opsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function RotaPage() {
  const session = await requireAuthenticatedSession("/dashboard/rota");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "organisation.users.manage",
      "organisation.users.read",
      "visits.manage.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load rota." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const page = await fetchShifts({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F2.2"
          title="Staff rota"
          description="Organisation shifts. Overlaps are rejected by the API. Timezones are stored per shift."
        />
        <div className="flex gap-3 text-sm">
          <Link href="/dashboard/rota/new" className="rounded-md bg-teal-700 px-3 py-2 text-white">
            New shift
          </Link>
          <Link href="/dashboard/visits" className="rounded-md border border-slate-300 px-3 py-2">
            Visits
          </Link>
          <Link href="/dashboard/tasks" className="rounded-md border border-slate-300 px-3 py-2">
            Tasks
          </Link>
        </div>
        {page.items.length === 0 ? (
          <EmptyState title="No shifts" description="Create a shift to populate the rota." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((shift) => (
              <li key={shift.id} className="p-4 text-sm">
                <p className="font-medium text-forest-900">
                  {shift.shift_type} · {shift.status}
                </p>
                <p className="text-slate-600">
                  {new Date(shift.starts_at).toLocaleString()} →{" "}
                  {new Date(shift.ends_at).toLocaleString()}
                </p>
                <p className="font-mono text-xs text-slate-500">{shift.staff_user_id}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return <ErrorState description={error instanceof Error ? error.message : "Failed to load rota."} />;
  }
}
