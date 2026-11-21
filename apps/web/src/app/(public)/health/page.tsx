import { HealthPanel } from "@/components/HealthPanel";

export default function HealthPage() {
  return (
    <section className="mx-auto max-w-xl">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">System</p>
      <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-navy-900 md:text-3xl">Service status</h1>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Shows whether this website is running. It does not check organisation data or other services.
      </p>
      <HealthPanel />
    </section>
  );
}
