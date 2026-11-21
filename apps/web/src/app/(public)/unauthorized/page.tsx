import Link from "next/link";
import { btnPrimary, btnSecondary } from "@/components/ui/primitives";

export default function UnauthorizedPage() {
  return (
    <div className="mx-auto max-w-xl">
      <div className="flex flex-col items-center rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center shadow-card">
        <span
          aria-hidden="true"
          className="flex h-14 w-14 items-center justify-center rounded-2xl border border-amber-100 bg-amber-50 text-amber-600"
        >
          <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="5" y="11" width="14" height="9" rx="2" />
            <path d="M8 11V8a4 4 0 0 1 8 0v3" />
          </svg>
        </span>
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-navy-900">Access denied</h1>
        <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">
          You&apos;re signed in, but your role doesn&apos;t include access to this page. Please contact your
          organisation admin if you think you need it.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link className={btnPrimary} href="/dashboard">
            Dashboard
          </Link>
          <Link className={btnSecondary} href="/account">
            Account
          </Link>
          <Link className={btnSecondary} href="/">
            Home
          </Link>
        </div>
      </div>
    </div>
  );
}
