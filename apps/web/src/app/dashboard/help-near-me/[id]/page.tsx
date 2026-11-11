import Link from "next/link";
import { redirect } from "next/navigation";
import { ReportModerationActions } from "@/components/community/ReportModerationActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Auth0 not configured" description="Cannot load report." />;
  }
  const { id } = await params;
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const report = await getAdminReport({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      reportId: id,
    });
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow="F5.2"
          title={report.service_name ?? "Service report"}
          description={`${report.reason.replaceAll("_", " ")} · ${report.status.replaceAll("_", " ")}`}
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link href="/dashboard/help-near-me" className="rounded-md border border-slate-300 px-3 py-2">
            Back to reports
          </Link>
          <Link
            href={`/dashboard/community-directory/${report.service_id}`}
            className="rounded-md bg-teal-700 px-3 py-2 text-white"
          >
            Open service listing
          </Link>
        </div>
        <dl className="grid gap-4 rounded-lg border border-slate-200 bg-white p-5 sm:grid-cols-2">
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
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load report."} />
    );
  }
}
