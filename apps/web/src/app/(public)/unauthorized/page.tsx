import Link from "next/link";

export default function UnauthorizedPage() {
  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-3xl font-semibold text-forest-900">Access denied</h1>
      <p className="text-slate-700">
        You are signed in, but your HMore role does not include permission for this action.
        Contact an Organisation Admin if you need access.
      </p>
      <div className="flex gap-3">
        <Link
          className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
          href="/account"
        >
          Account
        </Link>
        <Link
          className="rounded-md px-4 py-2 text-sm text-forest-900 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
          href="/dashboard"
        >
          Dashboard
        </Link>
        <Link
          className="rounded-md px-4 py-2 text-sm text-forest-900 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
          href="/"
        >
          Home
        </Link>
      </div>
    </div>
  );
}
