import type { ReactNode } from "react";
import Link from "next/link";

/**
 * Blue & White design-system primitives (docs/audit/HMORE_UI_UX_DESIGN_SPEC_COMPLETE_BLUE.pdf §3).
 * Server-component safe: no hooks, no client state.
 */

export const btnPrimary =
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-slate-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";
export const btnSecondary =
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600";
export const btnSoft =
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-brand-50 px-4 text-sm font-semibold text-brand-700 hover:bg-brand-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600";
export const btnDanger =
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-red-600 px-4 text-sm font-semibold text-white hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-2";
export const inputClass =
  "block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100";
export const labelClass = "block text-sm font-medium text-slate-800";
export const linkClass = "font-semibold text-brand-700 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600";

export type Tone = "green" | "amber" | "red" | "blue" | "indigo" | "gray";

const TONES: Record<Tone, string> = {
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/15",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
  red: "bg-red-50 text-red-700 ring-red-600/15",
  blue: "bg-brand-50 text-brand-700 ring-brand-700/15",
  indigo: "bg-indigo-50 text-indigo-700 ring-indigo-600/15",
  gray: "bg-slate-100 text-slate-600 ring-slate-500/15",
};

const DOTS: Record<Tone, string> = {
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
  blue: "bg-brand-600",
  indigo: "bg-indigo-500",
  gray: "bg-slate-400",
};

/** Maps common workflow statuses to a tone. Unknown statuses are gray. */
export function toneForStatus(status: string | null | undefined): Tone {
  const s = (status ?? "").toLowerCase().replace(/[\s-]+/g, "_");
  if (/^(paid|active|approved|completed|complete|done|closed|resolved|valid|signed|accepted|published|ok|healthy|on_track|full)$/.test(s)) return "green";
  if (/^(pending|due|due_soon|review|needs_review|in_review|awaiting.*|submitted|draft_review|expiring|medium|scheduled_soon|partial)$/.test(s)) return "amber";
  if (/^(overdue|late|urgent|high|critical|rejected|failed|expired|denied|suspended|open_urgent|escalated|missed)$/.test(s)) return "red";
  if (/^(in_progress|assigned|booked|scheduled|new|open|acknowledged|running)$/.test(s)) return "blue";
  if (/^(info|unread|low)$/.test(s)) return "indigo";
  return "gray";
}

export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  const text = value.replace(/[_-]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function StatusChip({ status, tone, children }: { status?: string | null; tone?: Tone; children?: ReactNode }) {
  const t = tone ?? toneForStatus(status);
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${TONES[t]}`}>
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${DOTS[t]}`} />
      {children ?? humanize(status)}
    </span>
  );
}

export function Card({
  children,
  className = "",
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white shadow-card ${padded ? "p-5" : ""} ${className}`}>{children}</div>
  );
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {description ? <p className="mt-0.5 text-sm text-slate-500">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0 text-sm">{action}</div> : null}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "gray",
  href,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: Tone;
  href?: string;
}) {
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        {hint ? <StatusChip tone={tone}>{hint}</StatusChip> : null}
      </div>
      <p className="mt-3 text-3xl font-bold tracking-tight text-slate-900">{value}</p>
    </>
  );
  const cls = "block rounded-2xl border border-slate-200 bg-white p-5 shadow-card";
  return href ? (
    <Link
      href={href}
      className={`${cls} transition hover:border-brand-200 hover:shadow-lift focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600`}
    >
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function StatGrid({ children }: { children: ReactNode }) {
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{children}</div>;
}

/** Icon tile + title + description link card used for quick actions and module launchers. */
export function ActionTile({
  href,
  title,
  description,
  initials,
}: {
  href: string;
  title: string;
  description?: string;
  initials?: string;
}) {
  const mark = (initials ?? title.slice(0, 2)).toUpperCase();
  return (
    <Link
      href={href}
      className="group flex items-start gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-card transition hover:border-brand-200 hover:shadow-lift focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
    >
      <span
        aria-hidden="true"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-sm font-bold text-brand-700 group-hover:bg-brand-100"
      >
        {mark}
      </span>
      <span className="min-w-0">
        <span className="block font-semibold text-slate-900">{title}</span>
        {description ? <span className="mt-0.5 block text-sm text-slate-500">{description}</span> : null}
      </span>
    </Link>
  );
}

/** Row in an "Needs attention" list: tone dot, title, meta, optional link. */
export function AttentionItem({
  title,
  meta,
  tone = "gray",
  href,
}: {
  title: string;
  meta?: string;
  tone?: Tone;
  href?: string;
}) {
  const inner = (
    <>
      <span aria-hidden="true" className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${DOTS[tone]}`} />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold text-slate-900">{title}</span>
        {meta ? <span className="block truncate text-xs text-slate-500">{meta}</span> : null}
      </span>
    </>
  );
  return (
    <li>
      {href ? (
        <Link href={href} className="flex gap-3 rounded-lg px-2 py-2.5 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600">
          {inner}
        </Link>
      ) : (
        <div className="flex gap-3 px-2 py-2.5">{inner}</div>
      )}
    </li>
  );
}

/** Table wrapper with spec styling. Children are <thead>/<tbody>; use Th / Td cells. */
export function DataTable({ children, caption }: { children: ReactNode; caption?: string }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-card">
      <table className="min-w-full divide-y divide-slate-100 text-left text-sm">
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        {children}
      </table>
    </div>
  );
}

export function Th({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return (
    <th scope="col" className={`bg-slate-50/80 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 ${className}`}>
      {children}
    </th>
  );
}

export function Td({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return <td className={`border-t border-slate-100 px-4 py-3.5 align-middle text-slate-700 ${className}`}>{children}</td>;
}

export function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" }) {
  const parts = name.split(/[\s._@-]+/).filter(Boolean);
  const text = ((parts[0]?.[0] ?? "?") + (parts[1]?.[0] ?? "")).toUpperCase();
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-full bg-brand-100 font-bold text-brand-700 ${
        size === "sm" ? "h-8 w-8 text-xs" : "h-10 w-10 text-sm"
      }`}
    >
      {text}
    </span>
  );
}

/** Line chart from real points only. Renders nothing when there is no series. */
export function SeriesChart({
  title,
  caption,
  points,
}: {
  title: string;
  caption?: string;
  points: { label: string; value: number }[];
}) {
  const usable = points.filter((point) => Number.isFinite(point.value));
  if (usable.length === 0) return null;
  const width = 640;
  const height = 168;
  const max = Math.max(...usable.map((point) => point.value), 1);
  const coords = usable.map((point, index) => {
    const x = usable.length === 1 ? width / 2 : (index / (usable.length - 1)) * width;
    const y = height - 12 - (point.value / max) * (height - 28);
    return { ...point, x, y };
  });
  const line = coords.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const area = `${line} L${coords[coords.length - 1]?.x.toFixed(1)},${height} L${coords[0]?.x.toFixed(1)},${height} Z`;
  return (
    <Card className="h-full">
      <CardHeader title={title} action={caption ? <span className="text-xs font-medium text-slate-400">{caption}</span> : undefined} />
      <svg viewBox={`0 0 ${width} ${height}`} className="mt-2 h-44 w-full" role="img" aria-label={title}>
        <path d={area} fill="#dbeafe" />
        <path d={line} fill="none" stroke="#1d4ed8" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        {coords.map((point, index) => (
          <circle key={`${point.label}-${index}`} cx={point.x} cy={point.y} r="4" fill="#1d4ed8" />
        ))}
      </svg>
      <div className="mt-2 flex justify-between gap-2 text-[11px] text-slate-400">
        <span className="truncate">{usable[0]?.label}</span>
        <span className="truncate">{usable[usable.length - 1]?.label}</span>
      </div>
    </Card>
  );
}

/** Pill filter tabs rendered as links (server-friendly). */
export function FilterTabs({ tabs }: { tabs: { label: string; href: string; active?: boolean; count?: number }[] }) {
  return (
    <nav aria-label="Filters" className="flex flex-wrap gap-2">
      {tabs.map((tab) => (
        <Link
          key={tab.href}
          href={tab.href}
          aria-current={tab.active ? "page" : undefined}
          className={`inline-flex h-8 items-center gap-1.5 rounded-full px-3.5 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
            tab.active ? "bg-brand-700 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          {tab.label}
          {typeof tab.count === "number" ? (
            <span className={`text-xs ${tab.active ? "text-brand-100" : "text-slate-400"}`}>{tab.count}</span>
          ) : null}
        </Link>
      ))}
    </nav>
  );
}


/** Vertical bar chart matching Blue & White design spec (§3, W-SA-01, W-OA-01, W-SW-01, W-TN-01). */
export function VerticalBarChart({
  title,
  caption,
  bars,
  yMax,
  highlightLast = true,
}: {
  title: string;
  caption?: string;
  bars: { label: string; value: number }[];
  yMax?: number;
  highlightLast?: boolean;
}) {
  const max = yMax ?? Math.max(...bars.map((b) => b.value), 1);
  return (
    <Card className="flex h-full flex-col justify-between">
      <CardHeader
        title={title}
        action={caption ? <span className="text-xs font-medium text-slate-400">{caption}</span> : undefined}
      />
      <div className="mt-2 flex flex-1 flex-col justify-end">
        <div className="flex h-44 items-end justify-between gap-2 px-2 pt-4">
          {bars.map((bar, idx) => {
            const heightPercent = Math.min(100, Math.max(8, (bar.value / max) * 100));
            const isLast = highlightLast && idx === bars.length - 1;
            return (
              <div key={bar.label + idx} className="group flex h-full flex-1 flex-col items-center justify-end gap-2">
                <div
                  className={`w-full rounded-t transition-all ${
                    isLast ? "bg-brand-700" : "bg-blue-100 hover:bg-blue-200"
                  }`}
                  style={{ height: `${heightPercent}%` }}
                  title={`${bar.label}: ${bar.value}`}
                />
              </div>
            );
          })}
        </div>
        <div className="mt-2 flex justify-between gap-1 border-t border-slate-100 px-1 pt-2 text-[10px] font-medium text-slate-400">
          {bars.map((bar, idx) => (
            <span key={bar.label + idx} className="flex-1 truncate text-center">
              {bar.label}
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
}
