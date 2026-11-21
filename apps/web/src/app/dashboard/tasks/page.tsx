import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, btnSecondary, DataTable, FilterTabs, humanize, inputClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchTasks } from "@/lib/opsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function tasksHref(next: { view?: string; status?: string; q?: string }) {
  const search = new URLSearchParams();
  if (next.view) search.set("view", next.view);
  if (next.status) search.set("status", next.status);
  if (next.q) search.set("q", next.q);
  const query = search.toString();
  return query ? `/dashboard/tasks?${query}` : "/dashboard/tasks";
}

export default async function TasksPage({
  searchParams,
}: {
  searchParams?: Promise<{ view?: string; status?: string; q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/tasks");
  const params = searchParams ? await searchParams : {};
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["tasks.manage.assigned", "tenants.manage"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see tasks." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Tasks will be available once sign-in is configured." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/tasks" />;
    const overdueOnly = params.view === "overdue";
    const q = (params.q ?? "").trim();
    const page = await fetchTasks({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      overdueOnly,
    });
    const statuses = [...new Set(page.items.map((task) => task.status).filter(Boolean))].sort();
    const status = statuses.includes(params.status ?? "") ? params.status ?? "" : "";
    const needle = q.toLowerCase();
    const visible = page.items.filter((task) => {
      if (status && task.status !== status) return false;
      if (!needle) return true;
      return task.title.toLowerCase().includes(needle);
    });
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="My work"
          title="Tasks"
          description="Work assigned to you, with anything overdue called out."
          actions={
            <Link href="/dashboard/tasks/new" className={btnPrimary}>
              + New task
            </Link>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {overdueOnly ? <input type="hidden" name="view" value="overdue" /> : null}
            {status ? <input type="hidden" name="status" value={status} /> : null}
            <label className="sr-only" htmlFor="task-search">
              Search tasks
            </label>
            <input id="task-search" name="q" defaultValue={q} placeholder="Search tasks" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: tasksHref({ q }), active: !overdueOnly && !status },
              { label: "Overdue", href: tasksHref({ view: "overdue", q }), active: overdueOnly && !status },
              ...statuses.map((item) => ({
                label: humanize(item),
                href: tasksHref({ view: overdueOnly ? "overdue" : undefined, q, status: item }),
                active: status === item,
              })),
            ]}
          />
        </div>
        {visible.length === 0 ? (
          <EmptyState
            title={overdueOnly ? "Nothing overdue" : "No tasks"}
            description={q || status ? "Nothing matches this search or status." : overdueOnly ? "Overdue tasks will show up here." : "Create a task when there is work to track."}
            action={q || status || overdueOnly ? { label: "Show all tasks", href: "/dashboard/tasks" } : undefined}
          />
        ) : (
          <DataTable caption="Tasks">
            <thead>
              <tr>
                <Th>Task</Th>
                <Th>Priority</Th>
                <Th>Due</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {visible.map((task) => (
                <tr key={task.id} className="hover:bg-slate-50/60">
                  <Td className="font-semibold text-slate-900">{task.title}</Td>
                  <Td>
                    <StatusChip status={task.priority} />
                  </Td>
                  <Td>{task.due_at ? new Date(task.due_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "—"}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-1.5">
                      <StatusChip status={task.status} />
                      {task.overdue ? <StatusChip status="overdue" /> : null}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <p className="text-sm text-slate-500">
          {visible.length === 0 ? `Showing 0 of ${page.total}` : `Showing 1–${visible.length} of ${page.total}`}
        </p>
      </div>
    );
  } catch (error) {
    return <ErrorState description={error instanceof Error ? error.message : "We couldn't load tasks. Please try again."} retryHref="/dashboard/tasks" />;
  }
}
