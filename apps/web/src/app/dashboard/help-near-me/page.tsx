import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnSecondary, DataTable, FilterTabs, inputClass, linkClass, StatusChip, Td, Th } from "@/components/ui/primitives";
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
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to review reports." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Help Near Me reports will be available once sign-in is configured." />;
  }
  const params = searchParams ? await searchParams : {};
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/help-near-me" />;
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
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Community"
          title="Help Near Me reports"
          description="Tenant reports ask for a review. They never verify or remove a listing on their own."
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {params.status ? <input type="hidden" name="status" value={params.status} /> : null}
            <label className="sr-only" htmlFor="report-search">
              Search reports
            </label>
            <input id="report-search" name="q" defaultValue={params.q ?? ""} placeholder="Search reports" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: "/dashboard/help-near-me", active: !params.status },
              { label: "Submitted", href: "/dashboard/help-near-me?status=submitted", active: params.status === "submitted" },
              { label: "Under review", href: "/dashboard/help-near-me?status=under_review", active: params.status === "under_review" },
              { label: "Directory", href: "/dashboard/community-directory" },
            ]}
          />
        </div>
        {result.items.length === 0 ? (
          <EmptyState
            title="No reports"
            description={params.status || params.q ? "No reports match these filters." : "Submitted tenant reports appear here for moderation."}
            action={params.status || params.q ? { label: "Clear filters", href: "/dashboard/help-near-me" } : undefined}
          />
        ) : (
          <DataTable caption="Help Near Me reports">
            <thead>
              <tr>
                <Th>Service</Th>
                <Th>Reason</Th>
                <Th>Submitted</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {result.items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/60">
                  <Td>
                    <Link href={`/dashboard/help-near-me/${row.id}`} className={linkClass}>
                      {row.service_name ?? "Service report"}
                    </Link>
                    <p className="mt-0.5 text-xs text-slate-500">{row.service_category?.replaceAll("_", " ") ?? "Service"}</p>
                  </Td>
                  <Td>{row.reason.replaceAll("_", " ")}</Td>
                  <Td>{new Date(row.created_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</Td>
                  <Td>
                    <StatusChip status={row.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </div>
    );
  } catch {
    return (
      <ErrorState description={"We couldn't load reports. Please try again."} retryHref="/dashboard/help-near-me" />
    );
  }
}
