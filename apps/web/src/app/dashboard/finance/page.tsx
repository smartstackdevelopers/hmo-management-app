import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { FinanceBoard } from "./FinanceBoard";

const READ = ["finance.records.read", "finance.reports.view", "finance.records.manage"];

export default async function FinancePage() {
  const session = await requireAuthenticatedSession("/dashboard/finance");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see finance." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so finance can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/finance" />;
  const perms = session.authorization?.permissions ?? [];
  return (
    <FinanceBoard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canAny(perms, ["finance.records.manage"])}
      canBudget={canAny(perms, ["finance.budgets.read", "finance.budgets.manage"])}
      canExport={canAny(perms, ["finance.exports", "reports.export.csv"])}
    />
  );
}
