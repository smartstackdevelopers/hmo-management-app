import Link from "next/link";
import { AuthShell, authPrimaryButtonClass } from "@/components/auth/AuthShell";

const STEPS = [
  { title: "Request sent", body: "We have your details and requested role.", state: "done" },
  {
    title: "Admin review",
    body: "Your housing provider checks your request — usually within 1 working day.",
    state: "current",
  },
  { title: "Access granted", body: "Sign in and you’ll land on your own home screen.", state: "next" },
] as const;

export default function RegisterPendingPage() {
  return (
    <AuthShell headline="Thanks — we’ve got your request." subline="Every account is approved by a person before it can see housing or support records.">
      <span
        aria-hidden="true"
        className="flex h-14 w-14 items-center justify-center rounded-2xl border border-brand-100 bg-brand-50 text-brand-700"
      >
        <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <circle cx="12" cy="12" r="8.5" />
          <path d="M12 7.5V12l3 2" />
        </svg>
      </span>
      <h1 className="mt-5 text-3xl font-bold tracking-tight text-slate-900">You’re almost in</h1>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Your account is waiting for approval. You don’t need to do anything else right now.
      </p>
      <ol className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        {STEPS.map((step, index) => (
          <li key={step.title} className="flex gap-4">
            <div className="flex flex-col items-center">
              <span
                aria-hidden="true"
                className={`flex h-6 w-6 items-center justify-center rounded-full ${
                  step.state === "done"
                    ? "bg-brand-700 text-white"
                    : step.state === "current"
                      ? "border-[6px] border-brand-700 bg-white"
                      : "border-2 border-slate-300 bg-white"
                }`}
              >
                {step.state === "done" ? (
                  <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m5 10.5 3.2 3L15 6.5" />
                  </svg>
                ) : null}
              </span>
              {index < STEPS.length - 1 ? (
                <span aria-hidden="true" className={`my-1 w-0.5 flex-1 ${step.state === "done" ? "bg-brand-700" : "bg-slate-200"}`} />
              ) : null}
            </div>
            <div className="pb-5">
              <p className={`text-sm font-semibold ${step.state === "next" ? "text-slate-400" : "text-slate-900"}`}>
                {step.title}
                {step.state === "current" ? <span className="sr-only"> (current step)</span> : null}
              </p>
              <p className="mt-0.5 text-sm text-slate-600">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
      <Link href="/login" className={`${authPrimaryButtonClass} mt-6`}>
        Go to sign in
      </Link>
    </AuthShell>
  );
}
