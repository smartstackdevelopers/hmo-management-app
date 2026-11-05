import Link from "next/link";

export default function HomePage() {
  return (
    <section className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-semibold tracking-tight text-forest-900 md:text-4xl">
        One shared platform for housing and support
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-slate-700">
        This is the HMore web foundation. Super Admin, Organisation Admin, and Landlord use the
        authenticated dashboard shell. Room Ready Expo remains the mobile reference.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
          href="/dashboard"
        >
          Open dashboard
        </Link>
        <Link
          className="rounded-md px-4 py-2 text-sm text-forest-900 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700"
          href="/auth/login?returnTo=/dashboard"
        >
          Sign in
        </Link>
      </div>
      <dl className="mt-10 grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <dt className="text-sm text-slate-500">Web</dt>
          <dd className="mt-1 font-medium">Next.js + Tailwind</dd>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <dt className="text-sm text-slate-500">API</dt>
          <dd className="mt-1 font-medium">Python FastAPI</dd>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm">
          <dt className="text-sm text-slate-500">Mobile</dt>
          <dd className="mt-1 font-medium">Expo in room-ready</dd>
        </div>
      </dl>
    </section>
  );
}
