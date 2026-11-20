export function LoadingState({ label = "Loading…", rows = 4 }: { label?: string; rows?: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="animate-pulse space-y-4">
        <div className="h-4 w-1/3 rounded bg-slate-100" />
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-xl bg-slate-100" />
            <div className="flex-1 space-y-2">
              <div className="h-3 rounded bg-slate-100" style={{ width: `${70 - (i % 3) * 12}%` }} />
              <div className="h-3 w-1/3 rounded bg-slate-50" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
