import type { ReactNode } from "react";
import Link from "next/link";
import { MobileNav } from "@/components/dashboard/MobileNav";
import { OrgContextBadge } from "@/components/dashboard/OrgContextBadge";
import { PathAwareSidebar } from "@/components/dashboard/PathAwareSidebar";
import { UserMenu } from "@/components/dashboard/UserMenu";
import { roleDisplayName } from "@/lib/dashboardAccess";
import { DASHBOARD_NAV, filterNavItems } from "@/lib/navigation";
import type { DashboardSession } from "@/lib/session";

type DashboardShellProps = {
  children: ReactNode;
  session: DashboardSession;
  title?: string;
};

export function DashboardShell({
  children,
  session,
  title = "HMore",
}: DashboardShellProps) {
  const permissions = session.authorization?.permissions;
  const role = session.authorization?.active_role ?? null;
  const navItems = filterNavItems(DASHBOARD_NAV, {
    authenticated: session.authenticated,
    permissions,
    role,
  });

  return (
    <div className="min-h-screen bg-cream text-slate-900">
      <MobileNav items={navItems} brand={title} />
      <div className="md:grid md:grid-cols-[16rem_1fr]">
        <aside
          className="hidden bg-forest-900 px-5 py-8 text-white md:flex md:min-h-screen md:flex-col md:gap-8"
          aria-label="Dashboard navigation"
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200">
              HMore
            </p>
            <p className="mt-3 text-xl font-semibold">{title}</p>
            <p className="mt-2 text-sm text-emerald-100/80">
              Authenticated dashboard shell for Super Admin, Organisation Admin, and Landlord.
            </p>
          </div>
          <OrgContextBadge
            organisationId={session.authorization?.active_organisation_id}
            roleLabel={roleDisplayName(role)}
          />
          {session.authenticated ? (
            <PathAwareSidebar items={navItems} />
          ) : (
            <p className="text-sm text-emerald-100/80">Sign in to see navigation.</p>
          )}
          <div className="mt-auto border-t border-white/10 pt-6">
            <UserMenu
              authenticated={session.authenticated}
              authConfigured={session.authConfigured}
              name={session.user?.name}
              email={session.user?.email}
            />
          </div>
        </aside>
        <div className="flex min-h-screen flex-col">
          <header
            className="hidden border-b border-slate-200 bg-white/80 px-6 py-4 backdrop-blur md:flex md:items-center md:justify-between"
            aria-label="Dashboard header"
          >
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Dashboard</p>
              <p className="text-sm font-medium text-forest-900">
                {roleDisplayName(role)}
                {session.authorization?.active_organisation_id
                  ? ` · org ${session.authorization.active_organisation_id.slice(0, 8)}…`
                  : ""}
              </p>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <Link
                className="rounded-md px-3 py-2 text-forest-900 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
                href="/"
              >
                Public home
              </Link>
              {session.authenticated ? (
                <Link
                  className="rounded-md bg-teal-700 px-3 py-2 font-medium text-white hover:bg-teal-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
                  href="/auth/logout"
                >
                  Log out
                </Link>
              ) : (
                <Link
                  className="rounded-md bg-teal-700 px-3 py-2 font-medium text-white hover:bg-teal-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
                  href="/auth/login?returnTo=/dashboard"
                >
                  Sign in
                </Link>
              )}
            </div>
          </header>
          <main id="main-content" tabIndex={-1} className="flex-1 px-4 py-8 md:px-10">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
