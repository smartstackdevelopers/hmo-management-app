export default function HomePage() {
  return (
    <section className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-semibold tracking-tight text-forest-900 md:text-4xl">
        One shared platform for housing and support
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-slate-700">
        This is the HMore web foundation. The production dashboard will use this Next.js app. The
        existing Room Ready Expo project remains the mobile reference. Business modules start in later
        Phase 1 items.
      </p>
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
