import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listAdminReports } from "@/lib/helpNearMeApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function HelpNearMeModerationPage({
  searchParams,
}: {
  searchParams?: Promise<{ status?: string; category?: string; q?: string; page?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/help-near-me");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "organisations.manage",
      "organisation.settings.manage",
    ]) &&
    session.authorization.active_role !== "organisation_admin" &&
    session.authorization.active_role !== "super_admin"
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load reports." />;
  }
  const params = searchParams ? await searchParams : {};
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const result = await listAdminReports({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      status: params.status,
      category: params.category,
      q: params.q,
      page,
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F5.2"
          title="Help Near Me reports"
          description="Tenant reports create review requests only. They never auto-verify or delete directory listings."
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link href="/dashboard/help-near-me" className="rounded-md border border-slate-300 px-3 py-2">
            All
          </Link>
          <Link
            href="/dashboard/help-near-me?status=submitted"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Submitted
          </Link>
          <Link
            href="/dashboard/help-near-me?status=under_review"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Under review
          </Link>
          <Link
            href="/dashboard/community-directory"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Community directory
          </Link>
        </div>
        <form className="flex flex-wrap gap-2" method="get">
          <input
            name="q"
            defaultValue={params.q ?? ""}
            placeholder="Search reports"
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          />
          {params.status ? <input type="hidden" name="status" value={params.status} /> : null}
          <button type="submit" className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            Search
          </button>
        </form>
        {result.items.length === 0 ? (
          <EmptyState title="No reports" description="Submitted tenant reports appear here for moderation." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {result.items.map((row) => (
              <li key={row.id} className="p-4 text-sm">
                <Link
                  href={`/dashboard/help-near-me/${row.id}`}
                  className="font-medium text-forest-900 hover:underline"
                >
                  {row.service_name ?? row.service_id}
                </Link>
                <p className="text-slate-700">
                  {row.reason.replaceAll("_", " ")} · {row.status.replaceAll("_", " ")}
                </p>
                <p className="text-slate-600">
                  {row.service_category?.replaceAll("_", " ") ?? "service"} ·{" "}
                  {new Date(row.created_at).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load reports."} />
    );
  }
}
