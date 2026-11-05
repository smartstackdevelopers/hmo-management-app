import { HealthPanel } from "@/components/HealthPanel";

export default function HealthPage() {
  return (
    <section className="mx-auto max-w-xl">
      <h1 className="text-2xl font-semibold text-forest-900">Service status</h1>
      <p className="mt-2 text-sm text-slate-600">
        Process health for this Next.js app. It does not report FastAPI or organisation data.
      </p>
      <HealthPanel />
    </section>
  );
}
