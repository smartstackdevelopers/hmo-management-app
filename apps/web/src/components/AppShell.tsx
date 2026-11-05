import type { ReactNode } from "react";
import Link from "next/link";

/** Public / lightly authenticated chrome. Role dashboards use DashboardShell. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen md:grid md:grid-cols-[16rem_1fr]">
      <aside className="bg-forest-900 px-6 py-8 text-white">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200">HMore</p>
        <p className="mt-3 text-2xl font-semibold">Web foundation</p>
        <p className="mt-2 text-sm text-emerald-100/80">
          Sign in to open the Super Admin, Organisation Admin, or Landlord dashboard shell.
        </p>
        <nav className="mt-8 flex flex-wrap gap-2 text-sm md:flex-col md:gap-1" aria-label="Public">
          <Link className="rounded-md bg-white/10 px-3 py-2 hover:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200" href="/">
            Home
          </Link>
          <Link className="rounded-md px-3 py-2 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200" href="/dashboard">
            Dashboard
          </Link>
          <Link className="rounded-md px-3 py-2 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200" href="/account">
            Account
          </Link>
          <Link className="rounded-md px-3 py-2 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200" href="/auth/login?returnTo=/dashboard">
            Sign in
          </Link>
          <Link className="rounded-md px-3 py-2 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200" href="/health">
            Service status
          </Link>
        </nav>
      </aside>
      <main className="px-6 py-10 md:px-10">{children}</main>
    </div>
  );
}
