import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { homePathForRole, isF19DashboardRole, roleDisplayName } from "@/lib/dashboardAccess";
import { LOGIN_PATH } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DashboardIndexPage() {
  const session = await requireAuthenticatedSession("/dashboard");

  if (!session.authConfigured) {
    return (
      <div className="mx-auto max-w-3xl">
        <PageHeader
          title="Dashboard unavailable"
          description="Auth0 is not configured in this environment. Add the variables from apps/web/.env.example to enable sign-in."
        />
        <EmptyState
          title="Sign-in not configured"
          description="CI and local builds can render this shell without a live Auth0 tenant."
          hint="Live role routing remains unverified until a real tenant is connected."
        />
      </div>
    );
  }

  if (session.authorizationError === "api_unreachable") {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          title="Dashboard"
          description="You are signed in, but the HMore API authorization snapshot could not be loaded."
        />
        <ErrorState description="Start the FastAPI service and ensure NEXT_PUBLIC_API_BASE_URL points at it. Role homes are not selected from client-side guesses." />
        <Link className="text-sm text-teal-800 underline" href="/account">
          Open account
        </Link>
      </div>
    );
  }

  if (session.authorizationError === "forbidden" || !session.authorization) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          title="No HMore role membership"
          description="Your Auth0 identity is valid, but no active HMore organisation membership was returned."
        />
        <EmptyState
          title="Membership required"
          description="Ask a Super Admin or Organisation Admin to assign one of the six approved roles."
        />
      </div>
    );
  }

  const role = session.authorization.active_role;
  if (isF19DashboardRole(role)) {
    redirect(homePathForRole(role));
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="No web dashboard home for this role"
        description={`Signed in as ${roleDisplayName(role)}. Tenant, Support Worker, and Maintenance dashboards are outside F1.9.`}
      />
      <EmptyState
        title="Use account or mobile"
        description="Day-to-day work for this role is not part of the Phase 1 web dashboard shell."
      />
      <Link
        className="inline-flex rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
        href="/account"
      >
        Account
      </Link>
      <p className="text-xs text-slate-500">
        If you reached this page unexpectedly, sign in again via{" "}
        <Link className="underline" href={`${LOGIN_PATH}?returnTo=/dashboard`}>
          login
        </Link>
        .
      </p>
    </div>
  );
}
