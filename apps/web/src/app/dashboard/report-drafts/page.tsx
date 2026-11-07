import { redirect } from "next/navigation";
import { ReportDraftsPanel } from "@/components/reports/ReportDraftsPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canGenerateReportDrafts, canReadReportDrafts } from "@/lib/reportDraftsView";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function ReportDraftsPage() {
  const session = await requireAuthenticatedSession("/dashboard/report-drafts");
  const permissions = session.authorization?.permissions ?? [];
  if (!canGenerateReportDrafts(permissions) && !canReadReportDrafts(permissions)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load report drafts." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          title="Report drafts"
          description="Weekly and monthly operational drafts from authorised F2.14 metrics. AI narrative requires human review and never auto-distributes."
        />
        <ReportDraftsPanel
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          permissions={permissions}
        />
      </div>
    );
  } catch {
    return <ErrorState description="Unable to load report drafts." />;
  }
}
