export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-6 py-10 text-center" role="status">
      <p className="text-sm font-medium text-slate-700">{label}</p>
    </div>
  );
}
