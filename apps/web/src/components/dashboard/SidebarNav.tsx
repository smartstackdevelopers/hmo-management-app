import Link from "next/link";
import { groupNavItemsByArea, isNavItemActive, type NavItem } from "@/lib/navigation";

type SidebarNavProps = {
  items: NavItem[];
  currentPath?: string;
};

const ALWAYS_OPEN = new Set(["overview"]);

export function SidebarNav({ items, currentPath = "" }: SidebarNavProps) {
  const areas = groupNavItemsByArea(items);

  return (
    <nav aria-label="Dashboard" className="space-y-1">
      {areas.map((area) => {
        const hasActive = area.items.some((item) => isNavItemActive(item, currentPath));
        const open = hasActive || ALWAYS_OPEN.has(area.id) || area.items.length <= 2;
        return (
          <details key={area.id} open={open} className="group/area">
            <summary className="flex min-h-9 cursor-pointer list-none items-center justify-between rounded-lg px-3 py-1.5 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-slate-400 hover:bg-slate-50 hover:text-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 [&::-webkit-details-marker]:hidden">
              <span>{area.label}</span>
              <span className="flex items-center gap-2">
                {!open ? (
                  <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[0.65rem] font-semibold tracking-normal text-slate-500">
                    {area.items.length}
                  </span>
                ) : null}
                <svg
                  aria-hidden="true"
                  viewBox="0 0 20 20"
                  className="h-3.5 w-3.5 transition-transform group-open/area:rotate-90"
                  fill="currentColor"
                >
                  <path d="M7.2 4.2a1 1 0 0 1 1.4 0l5 5a1 1 0 0 1 0 1.4l-5 5a1 1 0 1 1-1.4-1.4L11.5 10 7.2 5.6a1 1 0 0 1 0-1.4Z" />
                </svg>
              </span>
            </summary>
            <ul className="mb-2 mt-0.5 space-y-0.5">
              {area.items.map((item) => {
                const active = isNavItemActive(item, currentPath);
                return (
                  <li key={item.id}>
                    <Link
                      href={item.href}
                      className={`relative flex min-h-9 items-center gap-3 rounded-lg px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
                        active
                          ? "bg-brand-50 font-semibold text-brand-700"
                          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      }`}
                      aria-current={active ? "page" : undefined}
                    >
                      {active ? (
                        <span aria-hidden="true" className="absolute inset-y-1.5 left-0 w-1 rounded-full bg-brand-700" />
                      ) : null}
                      <span
                        aria-hidden="true"
                        className={`h-3.5 w-3.5 shrink-0 rounded ${
                          active ? "bg-brand-700" : "border-2 border-slate-300"
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </details>
        );
      })}
    </nav>
  );
}
