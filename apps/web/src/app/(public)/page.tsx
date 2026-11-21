import Link from "next/link";
import { btnPrimary, btnSecondary } from "@/components/ui/primitives";

const AUDIENCES = [
  {
    title: "Organisations",
    description: "Manage teams, homes, approvals and reports from one place.",
  },
  {
    title: "Landlords",
    description: "Keep properties, rooms, repairs and safety checks in good order.",
  },
  {
    title: "Tenants and support",
    description: "Stay in touch, raise repairs and get the right help at the right time.",
  },
];

export default function HomePage() {
  return (
    <section className="mx-auto max-w-4xl">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">Welcome to HMore</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight text-navy-900 md:text-4xl">
        One shared platform for housing and support
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
        HMore brings housing teams, landlords, support workers and tenants together, so everyone can see what
        needs doing and get on with it.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link className={btnPrimary} href="/dashboard">
          Open dashboard
        </Link>
        <Link className={btnSecondary} href="/auth/login?returnTo=/dashboard">
          Sign in
        </Link>
      </div>
      <ul className="mt-12 grid gap-4 sm:grid-cols-3">
        {AUDIENCES.map((item) => (
          <li key={item.title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <span
              aria-hidden="true"
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-sm font-bold text-brand-700"
            >
              {item.title.slice(0, 2).toUpperCase()}
            </span>
            <h2 className="mt-4 font-semibold text-slate-900">{item.title}</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">{item.description}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
