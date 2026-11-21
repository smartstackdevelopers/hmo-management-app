import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, linkClass } from "@/components/ui/primitives";
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
          description="Sign-in isn't set up in this environment yet, so role homes can't load."
        />
        <EmptyState
          title="Sign-in not configured"
          description="This shell can render without a live sign-in service."
          hint="Role homes stay unavailable until sign-in is connected."
        />
      </div>
    );
  }

  if (session.authorizationError === "api_unreachable") {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          title="Dashboard"
          description="You are signed in, but your access details could not be loaded."
        />
        <ErrorState
          description={
            session.authorizationDetail ??
            "The service that checks your access didn't respond. Try again in a moment."
          }
        />
        <Link className={linkClass} href="/account">
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
          description="You're signed in, but no active organisation membership was found."
        />
        <EmptyState
          title="Membership required"
          description="Ask a Super Admin or Organisation Admin to give you a role."
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
        description={`Signed in as ${roleDisplayName(role)}. Open your account to continue.`}
      />
      <EmptyState
        title="Use your account"
        description="Day-to-day work for this role starts from your account page."
      />
      <Link className={btnPrimary} href="/account">
        Account
      </Link>
      <p className="text-sm text-slate-500">
        If you reached this page unexpectedly, sign in again via{" "}
        <Link className={linkClass} href={`${LOGIN_PATH}?returnTo=/dashboard`}>
          login
        </Link>
        .
      </p>
    </div>
  );
}
