import Link from "next/link";
import { AuthShell, authSecondaryButtonClass } from "@/components/auth/AuthShell";

const STEPS = [
  { title: "Account created", body: "Your request has been received", done: true },
  { title: "Admin review", body: "Organisation Admin or Super Admin", done: false },
  { title: "Access granted", body: "You can sign in and start", done: false },
] as const;

export default function RegisterPendingPage() {
  return (
    <AuthShell
      headline="Thanks — we’ve got your request."
      subline="You’ll receive an email as soon as an administrator approves your account."
      points={["Usually within 1 working day", "No action needed from you"]}
    >
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">Request pending</h1>
      <p className="mt-1.5 text-sm text-slate-600">Here’s what happens next.</p>
      <div className="mt-4 rounded-2xl border border-slate-200 bg-white px-6 pb-6 pt-5">
        <span
          aria-hidden="true"
          className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700"
        >
          <svg viewBox="0 0 24 24" className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="12" cy="12" r="8.5" />
            <path d="M12 7.5V12l3 2" />
          </svg>
        </span>
        <ol className="mt-6 space-y-5">
          {STEPS.map((step) => (
            <li key={step.title} className="flex items-start gap-3">
              <span
                aria-hidden="true"
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
                  step.done ? "bg-brand-700 text-white" : "border border-slate-300 bg-white"
                }`}
              >
                {step.done ? (
                  <svg viewBox="0 0 20 20" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m5 10.5 3.2 3L15 6.5" />
                  </svg>
                ) : null}
              </span>
              <span>
                <span className="block text-sm font-semibold text-slate-900">
                  {step.title}
                  {step.done ? <span className="sr-only"> (done)</span> : null}
                </span>
                <span className="block text-xs text-slate-500">{step.body}</span>
              </span>
            </li>
          ))}
        </ol>
      </div>
      <Link href="/login" className={`${authSecondaryButtonClass} mt-5`}>
        Back to sign in
      </Link>
    </AuthShell>
  );
}
