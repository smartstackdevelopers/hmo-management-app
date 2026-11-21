import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { RecordPager } from "@/components/housing/RecordPager";
import { DataTable, FilterTabs, StatCard, StatGrid, StatusChip, Td, Th, btnPrimary, inputClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchComplaintDashboard, isComplaintOverdue, listComplaints } from "@/lib/complaintsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function complaintsHref(args: { q?: string; status?: string; priority?: string; overdue?: string; page?: number }) {
  const search = new URLSearchParams();
  if (args.q) search.set("q", args.q);
  if (args.status) search.set("status", args.status);
  if (args.priority) search.set("priority", args.priority);
  if (args.overdue) search.set("overdue", args.overdue);
  if (args.page && args.page > 1) search.set("page", String(args.page));
  const query = search.toString();
  return query ? `/dashboard/complaints?${query}` : "/dashboard/complaints";
}

export default async function ComplaintsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; priority?: string; overdue?: string; q?: string; page?: string }>;
}) {
  const params = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/complaints");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "complaints.manage",
      "complaints.read.own",
      "complaints.read.assigned",
      "complaints.create.own",
      "complaints.create.assigned",
      "complaints.read.property",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load complaints." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const role = session.authorization?.active_role;
    const q = params.q?.trim() || undefined;
    const pageNumber = Math.max(1, Number(params.page ?? "1") || 1);
    const [dashboard, page] = await Promise.all([
      fetchComplaintDashboard({ accessToken: token, organisationId: orgId, role }),
      listComplaints({
        accessToken: token,
        organisationId: orgId,
        role,
        status: params.status,
        priority: params.priority,
        overdueOnly: params.overdue === "1",
        q,
        page: pageNumber,
      }),
    ]);
    const canCreate = canAny(session.authorization?.permissions, [
      "complaints.manage",
      "complaints.create.own",
      "complaints.create.assigned",
    ]);
    const filtered = Boolean(params.status || params.priority || q || params.overdue === "1");
    const from = page.total === 0 ? 0 : (page.page - 1) * page.page_size + 1;
    const to = Math.min(page.page * page.page_size, page.total);
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Operations / Complaints"
          title="Complaints"
          description="Priorities, deadlines and escalations for complaints in this organisation."
          actions={
            canCreate ? (
              <Link href="/dashboard/complaints/new" className={btnPrimary}>
                New complaint
              </Link>
            ) : null
          }
        />
        <StatGrid>
          <StatCard label="Total" value={dashboard.total} />
          <StatCard label="Open" value={dashboard.open_count} />
          <StatCard
            label="Overdue"
            value={dashboard.overdue}
            hint={dashboard.overdue > 0 ? "Overdue" : undefined}
            tone="red"
            href="/dashboard/complaints?overdue=1"
          />
          <StatCard
            label="Escalated"
            value={dashboard.escalated}
            hint={dashboard.escalated > 0 ? "Escalated" : undefined}
            tone="red"
          />
          <StatCard label="Awaiting investigation" value={dashboard.awaiting_investigation} />
          <StatCard
            label="Upcoming deadlines"
            value={dashboard.upcoming_deadlines}
            hint={dashboard.upcoming_deadlines > 0 ? "Due soon" : undefined}
            tone="amber"
          />
          <StatCard label="Recently resolved" value={dashboard.recently_resolved} />
          <StatCard
            label="Urgent"
            value={dashboard.by_priority.urgent ?? 0}
            hint={(dashboard.by_priority.urgent ?? 0) > 0 ? "Urgent" : undefined}
            tone="red"
          />
        </StatGrid>
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="relative min-w-[16rem] flex-1">
            {params.status ? <input type="hidden" name="status" value={params.status} /> : null}
            {params.priority ? <input type="hidden" name="priority" value={params.priority} /> : null}
            {params.overdue === "1" ? <input type="hidden" name="overdue" value="1" /> : null}
            <label className="sr-only" htmlFor="complaint-search">
              Search complaints
            </label>
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" strokeLinecap="round" />
              </svg>
            </span>
            <input
              id="complaint-search"
              name="q"
              defaultValue={q ?? ""}
              placeholder="Search complaints"
              className={`${inputClass} pl-9`}
            />
            <button type="submit" className="sr-only">
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: complaintsHref({ q }), active: !params.overdue && !params.status && !params.priority },
              {
                label: "Overdue",
                href: complaintsHref({ q, overdue: "1" }),
                active: params.overdue === "1" && !params.status && !params.priority,
              },
            ]}
          />
        </div>
        {page.items.length === 0 ? (
          <EmptyState
            title="No complaints"
            description={filtered ? "No complaints match these filters." : "There are no complaints to show yet."}
            action={
              filtered
                ? { label: "Clear filters", href: "/dashboard/complaints" }
                : canCreate
                  ? { label: "New complaint", href: "/dashboard/complaints/new" }
                  : undefined
            }
          />
        ) : (
          <DataTable caption="Complaints">
            <thead>
              <tr>
                <Th>Complaint</Th>
                <Th>Reference</Th>
                <Th>Priority</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50">
                  <Td>
                    <Link
                      href={`/dashboard/complaints/${row.id}`}
                      className="font-semibold text-slate-900 hover:text-brand-700 hover:underline"
                    >
                      {row.title}
                    </Link>
                    {row.open_escalation ? (
                      <p className="mt-1 text-xs text-slate-500">Escalation open</p>
                    ) : null}
                  </Td>
                  <Td className="text-slate-500">{row.reference_number}</Td>
                  <Td>
                    <StatusChip status={row.priority} />
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-1.5">
                      <StatusChip status={row.status} />
                      {isComplaintOverdue(row) ? <StatusChip tone="red">Overdue</StatusChip> : null}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        {page.total > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-sm text-slate-500">
            <p>
              Showing {from}–{to} of {page.total}
            </p>
            <RecordPager
              page={pageNumber}
              pageCount={Math.max(1, Math.ceil(page.total / Math.max(page.page_size, 1)))}
              hrefFor={(next) =>
                complaintsHref({
                  q,
                  status: params.status,
                  priority: params.priority,
                  overdue: params.overdue,
                  page: next,
                })
              }
            />
          </div>
        ) : null}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Failed to load complaints."}
      />
    );
  }
}
