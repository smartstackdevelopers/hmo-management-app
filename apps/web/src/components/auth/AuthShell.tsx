import type { ReactNode } from "react";
import Link from "next/link";
import { BrandMark } from "@/components/brand/BrandMark";

const DEFAULT_POINTS = ["Role-based dashboards", "Approval-first access", "Council-ready records"];

type AuthShellProps = {
  children: ReactNode;
  headline?: string;
  subline?: string;
  points?: readonly string[];
};

export function AuthShell({
  children,
  headline = "Housing and support, managed with care.",
  subline = "One platform for organisations, landlords, support workers, contractors and tenants.",
  points = DEFAULT_POINTS,
}: AuthShellProps) {
  return (
    <div className="min-h-screen bg-cream lg:grid lg:grid-cols-[minmax(0,44fr)_minmax(0,56fr)]">
      <aside className="relative hidden overflow-hidden bg-navy-900 px-14 pb-10 pt-16 text-white lg:flex lg:flex-col">
        <span aria-hidden="true" className="absolute right-9 top-9 h-36 w-36 rounded-full bg-brand-700/70" />
        <span aria-hidden="true" className="absolute -right-0 bottom-14 h-72 w-72 rounded-full bg-brand-800/80" />
        <Link href="/" className="relative flex items-center gap-4 self-start rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-white">
          <BrandMark size="lg" />
          <span className="text-2xl font-bold tracking-tight">HMore</span>
        </Link>
        <div className="relative mt-24 max-w-lg">
          <h2 className="text-4xl font-bold leading-tight tracking-tight">{headline}</h2>
          <p className="mt-3 text-base leading-7 text-brand-100/90">{subline}</p>
          <ul className="mt-7 space-y-4">
            {points.map((point) => (
              <li key={point} className="flex items-center gap-3 text-sm font-semibold">
                <span aria-hidden="true" className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-600">
                  <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m5 10.5 3.2 3L15 6.5" />
                  </svg>
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative mt-auto text-xs text-brand-100/80">Secure · UK GDPR aware · Built for housing &amp; support providers</p>
      </aside>
      <main id="main-content" tabIndex={-1} className="flex min-h-screen flex-col px-6 py-10 sm:px-10 lg:pt-28">
        <Link href="/" className="mb-10 flex items-center gap-2.5 self-start lg:hidden">
          <BrandMark />
          <span className="text-lg font-bold text-navy-900">HMore</span>
        </Link>
        <div className="mx-auto w-full max-w-md">{children}</div>
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
  "mt-1.5 block h-11 w-full rounded-xl border border-slate-200 bg-white px-3.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-100";

export const authLabelClass = "block text-xs font-semibold text-slate-900";

export const authPrimaryButtonClass =
  "inline-flex h-12 w-full items-center justify-center rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";

export const authSecondaryButtonClass =
  "inline-flex h-11 w-full items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-900 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";

export const authLinkClass = "font-semibold text-brand-700 hover:underline";
