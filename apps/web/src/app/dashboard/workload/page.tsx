import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnSecondary, DataTable, inputClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchWorkload } from "@/lib/incidentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function WorkloadPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
  const session = await requireAuthenticatedSession("/dashboard/workload");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["workload.read", "workload.read.own"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see workload." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Workload will be available once sign-in is configured." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/workload" />;
    const data = await fetchWorkload({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    const q = (params.q ?? "").trim().toLowerCase();
    const visible = data.staff.filter((row) => !q || row.staff_user_id.toLowerCase().includes(q));
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Operations"
          title="Staff workload"
          description={`Live caseloads, tasks, visits, handovers and incident follow-ups (${data.scope}).`}
          actions={
            <Link href="/dashboard/incidents" className={btnSecondary}>
              Incidents
            </Link>
          }
        />
        <form method="get" className="flex min-w-[16rem] max-w-xl items-center gap-2">
          <label className="sr-only" htmlFor="workload-search">
            Search staff
          </label>
          <input id="workload-search" name="q" defaultValue={params.q ?? ""} placeholder="Search staff reference" className={inputClass} />
          <button type="submit" className={btnSecondary}>
            Search
          </button>
        </form>
        {visible.length === 0 ? (
          <EmptyState
            title="No workload yet"
            description={q ? "No staff reference matches this search." : "Rows appear when staff have assignments or open work."}
            action={q ? { label: "Clear search", href: "/dashboard/workload" } : undefined}
          />
        ) : (
          <DataTable caption="Staff workload">
            <thead>
              <tr>
                <Th>Staff</Th>
                <Th className="text-right">Tenants</Th>
                <Th className="text-right">Open tasks</Th>
                <Th className="text-right">Overdue tasks</Th>
                <Th className="text-right">Visits</Th>
                <Th className="text-right">Handovers</Th>
                <Th>Incident actions</Th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.staff_user_id} className="hover:bg-slate-50/60">
                  <Td className="font-mono text-xs text-slate-600">{row.staff_user_id}</Td>
                  <Td className="text-right tabular-nums">{row.assigned_tenants}</Td>
                  <Td className="text-right tabular-nums">{row.open_tasks}</Td>
                  <Td className="text-right tabular-nums">{row.overdue_tasks}</Td>
                  <Td className="text-right tabular-nums">{row.upcoming_visits}</Td>
                  <Td className="text-right tabular-nums">{row.pending_handovers}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-1.5">
                      <StatusChip tone="blue">{row.open_incident_follow_ups} open</StatusChip>
                      {row.overdue_incident_follow_ups > 0 ? (
                        <StatusChip status="overdue">{row.overdue_incident_follow_ups} overdue</StatusChip>
                      ) : null}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <p className="text-sm text-slate-500">
          {visible.length === 0 ? `Showing 0 of ${data.staff.length}` : `Showing 1–${visible.length} of ${data.staff.length}`}
        </p>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "We couldn't load workload. Please try again."} retryHref="/dashboard/workload" />
    );
  }
}
