import Link from "next/link";

type EmptyStateProps = {
  title: string;
  description: string;
  hint?: string;
  action?: { label: string; href: string };
};

export function EmptyState({ title, description, hint, action }: EmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center shadow-card"
      role="status"
    >
      <span
        aria-hidden="true"
        className="flex h-14 w-14 items-center justify-center rounded-2xl border border-brand-100 bg-brand-50 text-brand-700"
      >
        <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5z" />
          <path d="M4 7.5 12 12l8-4.5M12 12v9" />
        </svg>
      </span>
      <h2 className="mt-4 text-lg font-semibold text-slate-900">{title}</h2>
      <p className="mt-1.5 max-w-md text-sm leading-6 text-slate-600">{description}</p>
      {action ? (
        <Link
          href={action.href}
          className="mt-5 inline-flex h-10 items-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
        >
          {action.label}
        </Link>
      ) : null}
      {hint ? <p className="mt-4 max-w-md text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
