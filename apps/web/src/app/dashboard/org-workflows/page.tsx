import { redirect } from "next/navigation";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { ActionTile, StatCard, StatGrid, btnPrimary, btnSecondary } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchOrgWorkflowsDashboard } from "@/lib/orgWorkflowsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const ANY = ["approvals.inbox.read", "organisation.workflows.manage", "organisation.forms.manage"];

export default async function OrgWorkflowsDashboardPage() {
  const session = await requireAuthenticatedSession("/dashboard/org-workflows");
  if (session.authorization && !canAny(session.authorization.permissions, ANY)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  }
  const role = session.authorization?.active_role;
  let dashboard: Record<string, unknown> | null = null;
  try {
    dashboard = await fetchOrgWorkflowsDashboard({ accessToken: token, organisationId: orgId, role });
  } catch {
    return <ErrorState description={"Failed to load dashboard"} />;
  }
  const n = (k: string) => (typeof dashboard?.[k] === "number" ? (dashboard[k] as number) : "—");

  const stats = [
    ["Pending approvals", "pending_approvals", "amber"],
    ["Awaiting review", "awaiting_review", "amber"],
    ["Additional information", "additional_information_requests", "blue"],
    ["Overdue", "overdue_approvals", "red"],
    ["Active sharing grants", "active_secure_sharing_grants", "green"],
    ["Pending form submissions", "pending_form_submissions", "gray"],
  ] as const;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Approvals & workflows"
        description="Move requests from submitted to done."
        actions={
          <>
            <Link href="/dashboard/org-workflows/forms" className={btnSecondary}>
              Forms
            </Link>
            <Link href="/dashboard/org-workflows/workflows" className={btnPrimary}>
              Workflows
            </Link>
          </>
        }
      />
      <StatGrid>
        {stats.map(([label, key, tone]) => (
          <StatCard key={key} label={label} value={n(key)} tone={tone} />
        ))}
      </StatGrid>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <ActionTile href="/dashboard/org-workflows/approvals" title="Approvals inbox" description="Pending items you can review." initials="AP" />
        <ActionTile href="/dashboard/org-workflows/workflows" title="Workflow configuration" description="Versioned approval workflows." initials="WF" />
        <ActionTile href="/dashboard/org-workflows/forms" title="Custom forms" description="Organisation forms and submissions." initials="FM" />
        <ActionTile href="/dashboard/org-workflows/sharing" title="Secure sharing" description="Active grants. Tokens are shown once." initials="SH" />
        <ActionTile href="/dashboard/audit" title="Audit logs" description="Read-only record of sensitive actions." initials="AU" />
      </div>
    </div>
  );
}
