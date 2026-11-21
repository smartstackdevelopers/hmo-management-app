import Link from "next/link";
import { redirect } from "next/navigation";
import { ReportModerationActions } from "@/components/community/ReportModerationActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnSecondary, humanize, StatusChip } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { getAdminReport } from "@/lib/helpNearMeApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function HelpNearMeReportDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
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
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  const { id } = await params;
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
    const report = await getAdminReport({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      reportId: id,
    });
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow="Community"
          title={report.service_name ?? "Service report"}
          description={humanize(report.reason)}
          actions={
            <>
              <Link href="/dashboard/help-near-me" className={btnSecondary}>
                All reports
              </Link>
              <Link href={`/dashboard/community-directory/${report.service_id}`} className={btnSecondary}>
                Open service
              </Link>
            </>
          }
        />
        <StatusChip status={report.status} />
        <dl className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Details</dt>
            <dd className="mt-1 text-sm">{report.details?.trim() ? report.details : "No extra details"}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Submitted</dt>
            <dd className="mt-1 text-sm">{new Date(report.created_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Category</dt>
            <dd className="mt-1 text-sm">{report.service_category?.replaceAll("_", " ") ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Resolution notes</dt>
            <dd className="mt-1 text-sm">{report.resolution_notes ?? "—"}</dd>
          </div>
        </dl>
        <ReportModerationActions
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          reportId={report.id}
          currentStatus={report.status}
        />
      </div>
    );
  } catch {
    return (
      <ErrorState description={"Failed to load report."} />
    );
  }
}
