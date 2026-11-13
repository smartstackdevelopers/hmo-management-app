import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { getLmsLearnDashboard, listLmsCourses } from "@/lib/lmsApi";

const READ = ["lms.read", "lms.learn", "lms.manage", "lms.tenant.learn"];

export default async function LmsPage() {
  const session = await requireAuthenticatedSession("/dashboard/lms");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  let stats: Record<string, unknown> = {};
  let courses: Record<string, unknown>[] = [];
  try {
    stats = await getLmsLearnDashboard(token, orgId);
    courses = await listLmsCourses(token, orgId);
  } catch {
    return <ErrorState description="LMS add-on is disabled until LMS_GLOBAL_ENABLED and organisation settings are approved." />;
  }
  const byStatus = (stats.enrollments_by_status ?? {}) as Record<string, number>;
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Learning (LMS add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Progress and certificates are based on completed lessons and verified assessments — not simulated percentages.
        </p>
      </header>
      <section className="grid gap-4 sm:grid-cols-4">
        <Stat label="Assigned" value={String(byStatus.assigned ?? "0")} />
        <Stat label="In progress" value={String(byStatus.in_progress ?? "0")} />
        <Stat label="Completed" value={String(byStatus.completed ?? "0")} />
        <Stat label="Certificates" value={String(stats.certificates_count ?? "0")} />
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="font-medium text-slate-800">My courses</h2>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {courses.length === 0 ? (
            <li className="py-2 text-slate-500">No courses assigned yet.</li>
          ) : (
            courses.map((c) => (
              <li key={String(c.id)} className="flex justify-between py-2">
                <span>{String(c.title)}</span>
                <span className="text-slate-500">
                  {String(c.progress_percent ?? 0)}% — {String(c.status)}
                </span>
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}
