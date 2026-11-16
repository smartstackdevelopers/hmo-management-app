import Link from "next/link";

export default function RegisterPendingPage() {
  return (
    <main className="mx-auto max-w-lg space-y-4 p-8">
      <h1 className="text-3xl font-semibold text-slate-900">Registration pending</h1>
      <p className="text-slate-600">
        Your account was created with <strong>pending</strong> status. An administrator has been notified.
        You cannot access protected dashboards until approval.
      </p>
      <p className="text-sm text-slate-500">
        After approval, sign in at <Link className="underline" href="/login">/login</Link>.
      </p>
    </main>
  );
}
