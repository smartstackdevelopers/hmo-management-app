import Link from "next/link";

export function RecordPager({
  page,
  pageCount,
  hrefFor,
}: {
  page: number;
  pageCount: number;
  hrefFor: (page: number) => string;
}) {
  if (pageCount <= 1) return null;
  const end = Math.min(pageCount, Math.max(page, 1) + 1);
  const start = Math.max(1, end - 2);
  const numbers: number[] = [];
  for (let n = start; n <= Math.min(pageCount, start + 2); n += 1) numbers.push(n);
  const idle =
    "inline-flex h-8 w-8 items-center justify-center rounded-lg text-sm font-semibold text-slate-600 hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600";
  const current = "inline-flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-sm font-semibold text-white";
  const disabled = "inline-flex h-8 w-8 items-center justify-center rounded-lg text-sm font-semibold text-slate-300";
  return (
    <nav aria-label="Pagination" className="flex items-center gap-1">
      {page > 1 ? (
        <Link className={idle} href={hrefFor(page - 1)} aria-label="Previous page">
          ‹
        </Link>
      ) : (
        <span className={disabled} aria-hidden="true">
          ‹
        </span>
      )}
      {numbers.map((n) =>
        n === page ? (
          <span key={n} className={current} aria-current="page">
            {n}
          </span>
        ) : (
          <Link key={n} className={idle} href={hrefFor(n)}>
            {n}
          </Link>
        ),
      )}
      {page < pageCount ? (
        <Link className={idle} href={hrefFor(page + 1)} aria-label="Next page">
          ›
        </Link>
      ) : (
        <span className={disabled} aria-hidden="true">
          ›
        </span>
      )}
    </nav>
  );
}
