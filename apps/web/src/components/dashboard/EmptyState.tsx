type EmptyStateProps = {
  title: string;
  description: string;
  hint?: string;
};

export function EmptyState({ title, description, hint }: EmptyStateProps) {
  return (
    <div
      className="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-10 text-center"
      role="status"
    >
      <h2 className="text-lg font-semibold text-forest-900">{title}</h2>
      <p className="mt-2 text-sm text-slate-600">{description}</p>
      {hint ? <p className="mt-3 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
