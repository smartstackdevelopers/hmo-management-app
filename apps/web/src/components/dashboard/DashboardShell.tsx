import type { ReactNode } from "react";
import Link from "next/link";
import { BrandMark } from "@/components/brand/BrandMark";
import { MobileNav } from "@/components/dashboard/MobileNav";
import { OrgContextBadge } from "@/components/dashboard/OrgContextBadge";
import { PathAwareSidebar } from "@/components/dashboard/PathAwareSidebar";
import { UserMenu } from "@/components/dashboard/UserMenu";
import { roleDisplayName } from "@/lib/dashboardAccess";
import { DASHBOARD_NAV, filterNavItems } from "@/lib/navigation";
import { canRunOperationalSearch } from "@/lib/operationalSearchView";
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
  const roleLabel = roleDisplayName(role);
  const canSearch = session.authenticated && canRunOperationalSearch(permissions);
  const navItems = filterNavItems(DASHBOARD_NAV, {
    authenticated: session.authenticated,
    permissions,
    role,
  });

  return (
    <div className="min-h-screen bg-cream text-slate-900">
      <MobileNav items={navItems} brand={title} role={role} />
      <div className="md:grid md:grid-cols-[17rem_1fr]">
        <aside
          className="hidden border-r border-slate-200 bg-white md:sticky md:top-0 md:flex md:h-screen md:flex-col"
          aria-label="Dashboard navigation"
        >
          <div className="space-y-4 px-4 pb-4 pt-5">
            <Link
              href="/dashboard"
              className="flex items-center gap-3 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
            >
              <BrandMark />
              <span className="text-lg font-bold tracking-tight text-navy-900">{title}</span>
            </Link>
            <OrgContextBadge
              organisationId={session.authorization?.active_organisation_id}
              roleLabel={roleLabel}
            />
          </div>
          <div className="flex-1 overflow-y-auto px-3 pb-4">
            {session.authenticated ? (
              <PathAwareSidebar items={navItems} role={role} />
            ) : (
              <p className="px-3 text-sm text-slate-500">Sign in to see navigation.</p>
            )}
          </div>
          <div className="border-t border-slate-200 px-4 py-4">
            <UserMenu
              authenticated={session.authenticated}
              authConfigured={session.authConfigured}
              name={session.user?.name}
              email={session.user?.email}
              roleLabel={roleLabel}
            />
          </div>
        </aside>
        <div className="flex min-h-screen min-w-0 flex-col">
          <header
            className="sticky top-0 z-20 hidden h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white/90 px-8 backdrop-blur md:flex"
            aria-label="Dashboard header"
          >
            <form
              action={canSearch ? "/dashboard/operational-search" : "/properties"}
              role="search"
              className="w-full max-w-xl"
            >
              <label className="sr-only" htmlFor="dashboard-search">
                Search
              </label>
              <div className="flex h-10 items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 focus-within:border-brand-600 focus-within:bg-white focus-within:ring-2 focus-within:ring-brand-100">
                <svg aria-hidden="true" viewBox="0 0 20 20" className="h-4 w-4 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="9" cy="9" r="6" />
                  <path d="m14 14 4 4" strokeLinecap="round" />
                </svg>
                <input
                  id="dashboard-search"
                  name="q"
                  type="search"
                  placeholder="Search tenants, properties, jobs…"
                  className="h-full w-full bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
                />
                <span className="hidden rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-semibold text-slate-400 sm:inline">
                  Ctrl K
                </span>
              </div>
            </form>
            <div className="flex items-center gap-3 text-sm">
              <Link
                href="/dashboard/communications/inbox"
                aria-label="Messages"
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
              >
                <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9" strokeLinejoin="round" />
                  <path d="M10 20a2 2 0 0 0 4 0" strokeLinecap="round" />
                </svg>
              </Link>
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
                {roleLabel}
              </span>
              {session.authenticated ? (
                <Link
                  className="inline-flex h-10 items-center rounded-lg border border-slate-200 px-4 font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                  href="/auth/logout"
                >
                  Log out
                </Link>
              ) : (
                <Link
                  className="inline-flex h-10 items-center rounded-lg bg-brand-700 px-4 font-semibold text-white hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
                  href="/auth/login?returnTo=/dashboard"
                >
                  Sign in
                </Link>
              )}
            </div>
          </header>
          <main id="main-content" tabIndex={-1} className="flex-1 px-4 py-8 md:px-10">
            <div className="mx-auto w-full max-w-7xl">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
