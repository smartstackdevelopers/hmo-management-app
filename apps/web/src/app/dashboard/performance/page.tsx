import { redirect } from "next/navigation";
import { PerformanceDashboard } from "@/components/performance/PerformanceDashboard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = ["performance.read", "performance.benchmark.run", "platform.monitoring.read"];

export default async function PerformancePage() {
  const session = await requireAuthenticatedSession("/dashboard/performance");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const canRun = canAny(session.authorization?.permissions ?? [], ["performance.benchmark.run"]);
  return (
    <PerformanceDashboard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canRun={canRun}
    />
  );
}
