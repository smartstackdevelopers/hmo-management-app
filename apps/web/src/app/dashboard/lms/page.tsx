import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Avatar, DataTable, FilterTabs, StatCard, StatGrid, StatusChip, Td, Th, btnSecondary, inputClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { getLmsLearnDashboard, listLmsCourses } from "@/lib/lmsApi";

const READ = ["lms.read", "lms.learn", "lms.manage", "lms.tenant.learn"];

function text(value: unknown): string {
  return value == null || value === "" ? "—" : String(value);
}

export default async function LmsPage({
  searchParams,
}: {
  searchParams?: Promise<{ status?: string; q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/lms");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see learning." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so learning can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/lms" />;
  let stats: Record<string, unknown> = {};
  let courses: Record<string, unknown>[] = [];
  try {
    stats = await getLmsLearnDashboard(token, orgId);
    courses = await listLmsCourses(token, orgId);
  } catch {
    return (
      <ErrorState
        title="Learning unavailable"
        description="Learning isn't switched on for this organisation yet."
        retryHref="/dashboard/lms"
      />
    );
  }
  const params = searchParams ? await searchParams : {};
  const status = params.status === "in_progress" || params.status === "completed" ? params.status : "all";
  const query = (params.q ?? "").trim().toLowerCase();
  const visible = courses.filter((course) => {
    const matchesStatus = status === "all" || String(course.status) === status;
    const haystack = `${course.title ?? ""}`.toLowerCase();
    return matchesStatus && (!query || haystack.includes(query));
  });
  const byStatus = (stats.enrollments_by_status ?? {}) as Record<string, number>;
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="People / Learning"
        title="Learning"
        description="Courses for staff and tenants."
      />
      <div className="flex flex-wrap items-center gap-3">
        <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
          {status !== "all" ? <input type="hidden" name="status" value={status} /> : null}
          <label className="sr-only" htmlFor="course-search">
            Search courses
          </label>
          <input id="course-search" name="q" defaultValue={params.q ?? ""} placeholder="Search courses" className={inputClass} />
          <button type="submit" className={btnSecondary}>
            Search
          </button>
        </form>
        <FilterTabs
          tabs={[
            { label: "All", href: query ? `/dashboard/lms?q=${encodeURIComponent(query)}` : "/dashboard/lms", active: status === "all" },
            { label: "In progress", href: `/dashboard/lms?status=in_progress${query ? `&q=${encodeURIComponent(query)}` : ""}`, active: status === "in_progress" },
            { label: "Completed", href: `/dashboard/lms?status=completed${query ? `&q=${encodeURIComponent(query)}` : ""}`, active: status === "completed" },
          ]}
        />
      </div>
      <StatGrid>
        <StatCard label="Assigned" value={text(byStatus.assigned ?? 0)} />
        <StatCard label="In progress" value={text(byStatus.in_progress ?? 0)} tone="blue" />
        <StatCard label="Completed" value={text(byStatus.completed ?? 0)} tone="green" />
        <StatCard label="Certificates" value={text(stats.certificates_count ?? 0)} />
      </StatGrid>
      {visible.length === 0 ? (
        <EmptyState
          title={query || status !== "all" ? "No matching courses" : "No courses assigned"}
          description={query || status !== "all" ? "Nothing matches this view." : "Courses assigned to you will appear here."}
          action={query || status !== "all" ? { label: "Show all", href: "/dashboard/lms" } : undefined}
        />
      ) : (
        <DataTable caption="Courses">
          <thead>
            <tr>
              <Th>Course</Th>
              <Th>Progress</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((course) => (
              <tr key={text(course.id)} className="hover:bg-slate-50/60">
                <Td>
                  <span className="flex items-center gap-3">
                    <Avatar name={text(course.title)} size="sm" />
                    <span className="font-semibold text-slate-900">{text(course.title)}</span>
                  </span>
                </Td>
                <Td className="tabular-nums">{text(course.progress_percent ?? 0)}%</Td>
                <Td>
                  <StatusChip status={text(course.status)} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {visible.length === 0 ? "0" : `1–${visible.length}`} of {courses.length}
      </p>
    </div>
  );
}
