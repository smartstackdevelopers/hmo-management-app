import type { ReactNode } from "react";
import Link from "next/link";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen md:grid md:grid-cols-[16rem_1fr]">
      <aside className="bg-forest-900 px-6 py-8 text-white">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200">HMore</p>
        <p className="mt-3 text-2xl font-semibold">Web dashboard</p>
        <p className="mt-2 text-sm text-emerald-100/80">
          Next.js shell for Super Admin, Organisation Admin and Landlord. Sign-in uses Auth0.
        </p>
        <nav className="mt-8 flex gap-4 text-sm md:flex-col">
          <Link className="rounded-md bg-white/10 px-3 py-2 hover:bg-white/15" href="/">
            Home
          </Link>
          <Link className="rounded-md px-3 py-2 hover:bg-white/10" href="/account">
            Account
          </Link>
          <Link className="rounded-md px-3 py-2 hover:bg-white/10" href="/auth/login?returnTo=/account">
            Sign in
          </Link>
          <Link className="rounded-md px-3 py-2 hover:bg-white/10" href="/health">
            Service status
          </Link>
        </nav>
      </aside>
      <main className="px-6 py-10 md:px-10">{children}</main>
    </div>
  );
}
