import Link from "next/link";

type ErrorStateProps = {
  title?: string;
  description: string;
  retryHref?: string;
};

export function ErrorState({
  title = "Something went wrong",
  description,
  retryHref,
}: ErrorStateProps) {
  return (
    <div
      className="flex flex-col items-center rounded-2xl border border-red-100 bg-white px-6 py-10 text-center shadow-card"
      role="alert"
    >
      <span
        aria-hidden="true"
        className="flex h-14 w-14 items-center justify-center rounded-2xl border border-red-100 bg-red-50 text-red-600"
      >
        <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <path d="M12 8v5M12 16.5v.5" />
          <path d="M10.3 3.9 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" strokeLinejoin="round" />
        </svg>
      </span>
      <h2 className="mt-4 text-lg font-semibold text-slate-900">{title}</h2>
      <p className="mt-1.5 max-w-md text-sm leading-6 text-slate-600">{description}</p>
      {retryHref ? (
        <Link
          href={retryHref}
          className="mt-5 inline-flex h-10 items-center rounded-lg border border-slate-200 px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
        >
          Try again
        </Link>
      ) : null}
    </div>
  );
}
