import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchTasks } from "@/lib/opsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function TasksPage() {
  const session = await requireAuthenticatedSession("/dashboard/tasks");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["tasks.manage.assigned", "tenants.manage"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load tasks." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const page = await fetchTasks({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader eyebrow="F2.2" title="Tasks" description="Operational tasks with priority and overdue highlighting." />
        <Link href="/dashboard/tasks/new" className="inline-flex rounded-md bg-teal-700 px-3 py-2 text-sm text-white">
          New task
        </Link>
        {page.items.length === 0 ? (
          <EmptyState title="No tasks" description="Create a task for assigned operational work." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((task) => (
              <li key={task.id} className="flex items-start justify-between gap-3 p-4 text-sm">
                <div>
                  <p className="font-medium text-forest-900">{task.title}</p>
                  <p className="text-slate-600">
                    {task.status} · {task.priority}
                    {task.due_at ? ` · due ${new Date(task.due_at).toLocaleString()}` : ""}
                  </p>
                </div>
                {task.overdue ? (
                  <span className="rounded bg-red-100 px-2 py-1 text-xs font-medium text-red-800">Overdue</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return <ErrorState description={error instanceof Error ? error.message : "Failed to load tasks."} />;
  }
}
