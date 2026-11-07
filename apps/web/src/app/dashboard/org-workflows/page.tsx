import { redirect } from "next/navigation";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Auth0 not configured" description="Cannot load workflows." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }
  const role = session.authorization?.active_role;
  let dashboard: Record<string, unknown> | null = null;
  try {
    dashboard = await fetchOrgWorkflowsDashboard({ accessToken: token, organisationId: orgId, role });
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load dashboard"} />;
  }
  const n = (k: string) => (typeof dashboard?.[k] === "number" ? (dashboard[k] as number) : "—");

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="F2.13"
        title="Organisation workflows"
        description="Approvals inbox, custom forms, secure sharing, and audit access."
      />
      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="text-blue-700 underline" href="/dashboard/org-workflows/approvals">
          Approvals inbox
        </Link>
        <Link className="text-blue-700 underline" href="/dashboard/org-workflows/workflows">
          Workflow configuration
        </Link>
        <Link className="text-blue-700 underline" href="/dashboard/org-workflows/forms">
          Custom forms
        </Link>
        <Link className="text-blue-700 underline" href="/dashboard/org-workflows/sharing">
          Secure sharing
        </Link>
        <Link className="text-blue-700 underline" href="/dashboard/audit">
          Audit logs
        </Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(
          [
            ["Pending approvals", "pending_approvals"],
            ["Awaiting review", "awaiting_review"],
            ["Additional information", "additional_information_requests"],
            ["Overdue", "overdue_approvals"],
            ["Active sharing grants", "active_secure_sharing_grants"],
            ["Pending form submissions", "pending_form_submissions"],
          ] as const
        ).map(([label, key]) => (
          <div key={key} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm text-slate-600">{label}</div>
            <div className="text-2xl font-semibold text-slate-900">{n(key)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
