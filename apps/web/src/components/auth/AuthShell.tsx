import type { ReactNode } from "react";
import Link from "next/link";
import { BrandMark } from "@/components/brand/BrandMark";

const POINTS = ["Role-based dashboards", "Approval-first access", "Council-ready records"];

type AuthShellProps = {
  children: ReactNode;
  headline?: string;
  subline?: string;
};

export function AuthShell({
  children,
  headline = "Housing and support, managed with care.",
  subline = "One platform for organisations, landlords, support workers, contractors and tenants.",
}: AuthShellProps) {
  return (
    <div className="min-h-screen bg-cream lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="relative hidden overflow-hidden bg-navy-900 px-12 py-12 text-white lg:flex lg:flex-col">
        <span aria-hidden="true" className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-brand-800/60" />
        <span aria-hidden="true" className="absolute -bottom-32 -right-10 h-96 w-96 rounded-full bg-brand-900/70" />
        <Link href="/" className="relative flex items-center gap-3 self-start rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-white">
          <BrandMark size="lg" />
          <span className="text-2xl font-bold tracking-tight">HMore</span>
        </Link>
        <div className="relative my-auto max-w-md">
          <h2 className="text-4xl font-bold leading-tight tracking-tight">{headline}</h2>
          <p className="mt-4 text-base leading-7 text-brand-100/90">{subline}</p>
          <ul className="mt-8 space-y-3">
            {POINTS.map((point) => (
              <li key={point} className="flex items-center gap-3 text-sm font-semibold">
                <span aria-hidden="true" className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600">
                  <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m5 10.5 3.2 3L15 6.5" />
                  </svg>
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-brand-100/70">Secure · UK GDPR aware · Built for housing &amp; support providers</p>
      </aside>
      <main id="main-content" tabIndex={-1} className="flex min-h-screen flex-col px-6 py-10 sm:px-10">
        <Link href="/" className="mb-10 flex items-center gap-2.5 self-start lg:hidden">
          <BrandMark />
          <span className="text-lg font-bold text-navy-900">HMore</span>
        </Link>
        <div className="mx-auto my-auto w-full max-w-md">{children}</div>
      </main>
    </div>
  );
}

export function AuthAlert({ message }: { message: string }) {
  return (
    <div role="alert" className="flex gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <svg aria-hidden="true" viewBox="0 0 20 20" className="mt-0.5 h-4 w-4 shrink-0" fill="currentColor">
        <path d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm-.9 4.5h1.8v5h-1.8v-5Zm0 6.5h1.8v1.8h-1.8V13Z" />
      </svg>
      <p>{message}</p>
    </div>
  );
}

export const authInputClass =
  "mt-1.5 block h-11 w-full rounded-xl border border-slate-300 bg-white px-3.5 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100";

export const authLabelClass = "block text-sm font-medium text-slate-800";

export const authPrimaryButtonClass =
  "inline-flex h-12 w-full items-center justify-center rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";
