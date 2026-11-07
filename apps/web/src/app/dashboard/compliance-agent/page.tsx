import { redirect } from "next/navigation";
import { ComplianceAgentPanel } from "@/components/compliance/ComplianceAgentPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canRunComplianceSweep } from "@/lib/complianceAgentView";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function ComplianceAgentPage() {
  const session = await requireAuthenticatedSession("/dashboard/compliance-agent");
  const permissions = session.authorization?.permissions ?? [];
  if (!canRunComplianceSweep(permissions) && !permissions.includes("ai.compliance.read")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load compliance agent." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          title="Compliance agent"
          description="Rules-based sweep of existing HMore operational deadlines and expiry fields, with AI explanations for staff review."
        />
        <ComplianceAgentPanel
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          permissions={permissions}
        />
      </div>
    );
  } catch {
    return <ErrorState description="Unable to load compliance agent." />;
  }
}
