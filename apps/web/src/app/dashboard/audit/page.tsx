import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { redirect } from "next/navigation";

export default async function DashboardAuditPage() {
  const session = await requireAuthenticatedSession("/dashboard/audit");
  if (session.authorization && !can(session.authorization.permissions, "audit_logs.read")) {
    redirect("/unauthorized");
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="Audit logs"
        description="Read-only audit access is enforced by the API (audit_logs.read)."
      />
      <EmptyState
        title="Audit viewer not built in F1.9"
        description="Use GET /api/v1/audit-events with organisation context. This page is a shell destination only."
      />
    </div>
  );
}
