"use client";

type BarItem = { label: string; value: number };
type Slice = { label: string; value: number; color: string };

const COLORS = ["#0f766e", "#1d4ed8", "#b45309", "#be123c", "#4338ca", "#047857", "#7c2d12"];

export function SummaryCards({ items }: { items: { label: string; value: string | number }[] }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">No summary metrics for the current filters.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-slate-500">{item.label}</div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">{item.value}</div>
        </div>
      ))}
    </div>
  );
}

export function BarChart({ title, items }: { title: string; items: BarItem[] }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  if (!items.length) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
        No data for {title}.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-medium text-slate-800">{title}</h3>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="grid grid-cols-[8rem_1fr_3rem] items-center gap-2 text-sm">
            <span className="truncate text-slate-600" title={item.label}>
              {item.label}
            </span>
            <div className="h-3 overflow-hidden rounded bg-slate-100">
              <div
                className="h-full rounded bg-teal-700 transition-all duration-500"
                style={{ width: `${(item.value / max) * 100}%` }}
              />
            </div>
            <span className="text-right tabular-nums text-slate-800">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LineChart({
  title,
  points,
}: {
  title: string;
  points: { label: string; value: number }[];
}) {
  if (!points.length) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
        No trend data for {title}.
      </div>
    );
  }
  const max = Math.max(...points.map((p) => p.value), 1);
  const w = 480;
  const h = 160;
  const pad = 16;
  const coords = points.map((p, i) => {
    const x = pad + (i / Math.max(points.length - 1, 1)) * (w - pad * 2);
    const y = h - pad - (p.value / max) * (h - pad * 2);
    return `${x},${y}`;
  });
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-medium text-slate-800">{title}</h3>
      <svg viewBox={`0 0 ${w} ${h}`} className="h-40 w-full" role="img" aria-label={title}>
        <polyline
          fill="none"
          stroke="#0f766e"
          strokeWidth="2.5"
          points={coords.join(" ")}
          className="transition-all duration-500"
        />
        {points.map((p, i) => {
          const pair = coords[i] ?? "0,0";
          const [x, y] = pair.split(",").map(Number);
          return <circle key={p.label + i} cx={x} cy={y} r="3" fill="#0f766e" />;
        })}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-slate-500">
        <span>{points[0]?.label}</span>
        <span>{points[points.length - 1]?.label}</span>
      </div>
    </div>
  );
}

export function PieChart({ title, items }: { title: string; items: BarItem[] }) {
  const total = items.reduce((s, i) => s + i.value, 0);
  if (!total) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
        No distribution data for {title}.
      </div>
    );
  }
  let angle = 0;
  const slices: Slice[] = items
    .filter((i) => i.value > 0)
    .map((item, idx) => {
      const sweep = (item.value / total) * 360;
      const start = angle;
      angle += sweep;
      return { ...item, color: COLORS[idx % COLORS.length], start, sweep } as Slice & {
        start: number;
        sweep: number;
      };
    });
  const toXY = (deg: number, r = 40) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [50 + r * Math.cos(rad), 50 + r * Math.sin(rad)];
  };
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-medium text-slate-800">{title}</h3>
      <div className="flex flex-wrap items-center gap-4">
        <svg viewBox="0 0 100 100" className="h-36 w-36" role="img" aria-label={title}>
          {slices.map((slice) => {
            const s = slice as Slice & { start: number; sweep: number };
            if (s.sweep >= 359.9) {
              return <circle key={s.label} cx="50" cy="50" r="40" fill={s.color} />;
            }
            const [x1, y1] = toXY(s.start);
            const [x2, y2] = toXY(s.start + s.sweep);
            const large = s.sweep > 180 ? 1 : 0;
            const d = `M 50 50 L ${x1} ${y1} A 40 40 0 ${large} 1 ${x2} ${y2} Z`;
            return <path key={s.label} d={d} fill={s.color} />;
          })}
        </svg>
        <ul className="space-y-1 text-sm">
          {slices.map((s) => (
            <li key={s.label} className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
              <span className="text-slate-700">
                {s.label}: {s.value}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function DataTable({
  rows,
  emptyMessage = "No records match the current filters.",
}: {
  rows: Record<string, unknown>[];
  emptyMessage?: string;
}) {
  const first = rows[0];
  if (!first) {
    return <p className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">{emptyMessage}</p>;
  }
  const headers = Object.keys(first);
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h.replaceAll("_", " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={idx} className="border-t border-slate-100">
              {headers.map((h) => (
                <td key={h} className="px-3 py-2 text-slate-700">
                  {String(row[h] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
