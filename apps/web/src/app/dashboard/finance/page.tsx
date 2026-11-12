import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { FinanceDashboard } from "@/components/finance/FinanceDashboard";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = ["finance.records.read", "finance.reports.view", "finance.records.manage"];

export default async function FinancePage() {
  const session = await requireAuthenticatedSession("/dashboard/finance");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const perms = session.authorization?.permissions ?? [];
  return (
    <FinanceDashboard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canAny(perms, ["finance.records.manage"])}
      canBudget={canAny(perms, ["finance.budgets.read", "finance.budgets.manage"])}
      canExport={canAny(perms, ["finance.exports", "reports.export.csv"])}
    />
  );
}
