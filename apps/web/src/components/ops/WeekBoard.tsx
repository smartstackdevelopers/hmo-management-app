import Link from "next/link";
import { btnSecondary } from "@/components/ui/primitives";

export type WeekTone = "blue" | "indigo" | "amber" | "red" | "gray";

export type WeekEvent = {
  id: string;
  title: string;
  start: string;
  end?: string | null;
  tone?: WeekTone;
};

const TONE: Record<WeekTone, string> = {
  blue: "border-brand-600 bg-brand-50 text-brand-900",
  indigo: "border-indigo-500 bg-indigo-50 text-indigo-900",
  amber: "border-amber-500 bg-amber-50 text-amber-900",
  red: "border-red-500 bg-red-50 text-red-900",
  gray: "border-slate-400 bg-slate-100 text-slate-700",
};

const HOUR_START = 8;
const HOUR_END = 18;

function parseDay(value: string | undefined): Date {
  if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    if (!year || !month || !day) {
      const now = new Date();
      return new Date(now.getFullYear(), now.getMonth(), now.getDate());
    }
    return new Date(year, month - 1, day);
  }
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

export function isoDate(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, "0");
  const date = String(day.getDate()).padStart(2, "0");
  return `${day.getFullYear()}-${month}-${date}`;
}

function addDays(day: Date, count: number): Date {
  const next = new Date(day);
  next.setDate(next.getDate() + count);
  return next;
}

function startOfWeek(day: Date): Date {
  const start = new Date(day.getFullYear(), day.getMonth(), day.getDate());
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
  return start;
}

function sameDay(left: Date, right: Date): boolean {
  return isoDate(left) === isoDate(right);
}

function eventRange(event: WeekEvent): { start: Date; end: Date } | null {
  const start = new Date(event.start);
  if (Number.isNaN(start.getTime())) return null;
  const end = event.end ? new Date(event.end) : new Date(start.getTime() + 60 * 60 * 1000);
  if (Number.isNaN(end.getTime()) || end <= start) {
    return { start, end: new Date(start.getTime() + 60 * 60 * 1000) };
  }
  return { start, end };
}

function clock(value: Date): string {
  return value.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function WeekBoard({
  events,
  anchor,
  view,
  basePath,
  query,
}: {
  events: WeekEvent[];
  anchor?: string;
  view?: string;
  basePath: string;
  query?: Record<string, string | undefined>;
}) {
  const mode = view === "day" || view === "month" ? view : "week";
  const day = parseDay(anchor);
  const weekStart = startOfWeek(day);
  const days = Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
  const today = isoDate(new Date());

  function href(next: { anchor?: string; view?: string }) {
    const params = new URLSearchParams();
    if (query) {
      for (const [key, value] of Object.entries(query)) {
        if (value) params.set(key, value);
      }
    }
    if (next.anchor) params.set("week", next.anchor);
    if (next.view && next.view !== "week") params.set("view", next.view);
    const built = params.toString();
    return built ? `${basePath}?${built}` : basePath;
  }

  const weekFrom = days[0] ?? weekStart;
  const weekTo = days[6] ?? weekStart;
  const sameMonth = weekFrom.getMonth() === weekTo.getMonth() && weekFrom.getFullYear() === weekTo.getFullYear();
  const rangeLabel =
    mode === "day"
      ? day.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
      : mode === "month"
        ? day.toLocaleDateString("en-GB", { month: "long", year: "numeric" })
        : sameMonth
          ? `${weekFrom.getDate()} – ${weekTo.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}`
          : `${weekFrom.toLocaleDateString("en-GB", { day: "numeric", month: "short" })} – ${weekTo.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}`;

  const step = mode === "month" ? "month" : mode === "day" ? "day" : "week";
  const previous =
    step === "month"
      ? isoDate(new Date(day.getFullYear(), day.getMonth() - 1, 1))
      : isoDate(addDays(step === "day" ? day : weekStart, step === "day" ? -1 : -7));
  const following =
    step === "month"
      ? isoDate(new Date(day.getFullYear(), day.getMonth() + 1, 1))
      : isoDate(addDays(step === "day" ? day : weekStart, step === "day" ? 1 : 7));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Link href={href({ view: mode })} className={btnSecondary}>
            Today
          </Link>
          <Link
            href={href({ anchor: previous, view: mode })}
            aria-label="Previous"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-lg text-slate-700 hover:bg-slate-50"
          >
            ‹
          </Link>
          <Link
            href={href({ anchor: following, view: mode })}
            aria-label="Next"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-lg text-slate-700 hover:bg-slate-50"
          >
            ›
          </Link>
          <p className="text-sm font-semibold text-slate-900">{rangeLabel}</p>
        </div>
        <div className="flex rounded-lg border border-slate-200 bg-white p-1" role="group" aria-label="Calendar view">
          {(["day", "week", "month"] as const).map((item) => (
            <Link
              key={item}
              href={href({ anchor: isoDate(day), view: item })}
              aria-current={mode === item ? "true" : undefined}
              className={`rounded-md px-3 py-1.5 text-sm font-semibold capitalize ${
                mode === item ? "bg-brand-700 text-white" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {item}
            </Link>
          ))}
        </div>
      </div>
      {mode === "week" ? <WeekGrid days={days} events={events} today={today} /> : null}
      {mode === "day" ? <DayList day={day} events={events} /> : null}
      {mode === "month" ? <MonthList month={day} events={events} /> : null}
    </div>
  );
}

function WeekGrid({ days, events, today }: { days: Date[]; events: WeekEvent[]; today: string }) {
  const hours = Array.from({ length: HOUR_END - HOUR_START }, (_, index) => HOUR_START + index);
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-card">
      <div className="grid min-w-[760px] grid-cols-[4.5rem_repeat(7,minmax(0,1fr))]">
        <div className="border-b border-slate-100 bg-slate-50/80" />
        {days.map((day) => (
          <div key={isoDate(day)} className="border-b border-l border-slate-100 bg-slate-50/80 px-2 py-3 text-center">
            <p className={`text-xs font-semibold uppercase tracking-wide ${isoDate(day) === today ? "text-brand-700" : "text-slate-500"}`}>
              {day.toLocaleDateString("en-GB", { weekday: "short" })}
            </p>
            <p className={`text-sm font-semibold ${isoDate(day) === today ? "text-brand-700" : "text-slate-900"}`}>
              {day.getDate()}
            </p>
          </div>
        ))}
        <div>
          {hours.map((hour) => (
            <div key={hour} className="flex h-14 items-start justify-end pr-2 pt-1 text-xs text-slate-400">
              {String(hour).padStart(2, "0")}:00
            </div>
          ))}
        </div>
        {days.map((day) => (
          <div key={isoDate(day)} className="relative border-l border-slate-100">
            {hours.map((hour) => (
              <div key={hour} className="h-14 border-b border-slate-100" />
            ))}
            {events.map((event) => {
              const range = eventRange(event);
              if (!range || !sameDay(range.start, day)) return null;
              const startMinutes = range.start.getHours() * 60 + range.start.getMinutes();
              const endMinutes = range.end.getHours() * 60 + range.end.getMinutes();
              const windowStart = HOUR_START * 60;
              const windowEnd = HOUR_END * 60;
              if (endMinutes <= windowStart || startMinutes >= windowEnd) return null;
              const top = ((Math.max(startMinutes, windowStart) - windowStart) / (windowEnd - windowStart)) * 100;
              const bottom = ((Math.min(endMinutes, windowEnd) - windowStart) / (windowEnd - windowStart)) * 100;
              return (
                <div
                  key={event.id}
                  className={`absolute inset-x-1 overflow-hidden rounded-md border-l-4 px-2 py-1 text-xs leading-4 ${TONE[event.tone ?? "blue"]}`}
                  style={{ top: `${top}%`, height: `${Math.max(bottom - top, 8)}%` }}
                >
                  <p className="truncate font-semibold">{event.title}</p>
                  <p className="truncate opacity-80">{clock(range.start)}</p>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function DayList({ day, events }: { day: Date; events: WeekEvent[] }) {
  const rows = events
    .map((event) => ({ event, range: eventRange(event) }))
    .filter((row): row is { event: WeekEvent; range: { start: Date; end: Date } } => Boolean(row.range && sameDay(row.range.start, day)))
    .sort((left, right) => left.range.start.getTime() - right.range.start.getTime());
  if (rows.length === 0) {
    return <p className="rounded-2xl border border-slate-200 bg-white px-5 py-8 text-sm text-slate-500 shadow-card">Nothing scheduled on this day.</p>;
  }
  return (
    <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
      {rows.map(({ event, range }) => (
        <li key={event.id} className="flex items-start gap-3 px-4 py-3">
          <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${event.tone === "red" ? "bg-red-500" : event.tone === "amber" ? "bg-amber-500" : "bg-brand-600"}`} />
          <div>
            <p className="text-sm font-semibold text-slate-900">{event.title}</p>
            <p className="text-xs text-slate-500">
              {clock(range.start)} – {clock(range.end)}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function MonthList({ month, events }: { month: Date; events: WeekEvent[] }) {
  const rows = events
    .map((event) => ({ event, range: eventRange(event) }))
    .filter(
      (row): row is { event: WeekEvent; range: { start: Date; end: Date } } =>
        Boolean(row.range && row.range.start.getMonth() === month.getMonth() && row.range.start.getFullYear() === month.getFullYear()),
    )
    .sort((left, right) => left.range.start.getTime() - right.range.start.getTime());
  if (rows.length === 0) {
    return <p className="rounded-2xl border border-slate-200 bg-white px-5 py-8 text-sm text-slate-500 shadow-card">Nothing scheduled this month.</p>;
  }
  return (
    <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
      {rows.map(({ event, range }) => (
        <li key={event.id} className="flex items-start justify-between gap-3 px-4 py-3">
          <div>
            <p className="text-sm font-semibold text-slate-900">{event.title}</p>
            <p className="text-xs text-slate-500">{clock(range.start)}</p>
          </div>
          <p className="text-xs text-slate-500">
            {range.start.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })}
          </p>
        </li>
      ))}
    </ul>
  );
}
