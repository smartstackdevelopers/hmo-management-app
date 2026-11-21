import type { ReactNode } from "react";
import Link from "next/link";
import { BrandMark } from "@/components/brand/BrandMark";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/account", label: "Account" },
  { href: "/auth/login?returnTo=/dashboard", label: "Sign in" },
  { href: "/health", label: "Service status" },
];

/** Public / lightly authenticated chrome. Role dashboards use DashboardShell. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-cream md:grid md:grid-cols-[17rem_1fr]">
      <aside className="border-b border-slate-200 bg-white px-5 py-6 md:border-b-0 md:border-r" aria-label="Site navigation">
        <Link href="/" className="flex items-center gap-3 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600">
          <BrandMark />
          <span className="text-lg font-bold tracking-tight text-navy-900">HMore</span>
        </Link>
        <p className="mt-4 text-sm leading-6 text-slate-500">
          Housing, support and community — one platform for every role.
        </p>
        <nav className="mt-6 flex flex-wrap gap-1 text-sm md:flex-col" aria-label="Public">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              className="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-brand-50 hover:text-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
              href={link.href}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main id="main-content" tabIndex={-1} className="px-6 py-10 md:px-10">
        {children}
      </main>
    </div>
  );
}
