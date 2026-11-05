import Link from "next/link";
import { groupNavItems, type NavItem } from "@/lib/navigation";

const SECTION_LABELS: Record<string, string> = {
  primary: "Overview",
  records: "Records",
  platform: "Platform",
  account: "Account",
};

type SidebarNavProps = {
  items: NavItem[];
  currentPath?: string;
};

export function SidebarNav({ items, currentPath = "" }: SidebarNavProps) {
  const groups = groupNavItems(items);

  return (
    <nav aria-label="Dashboard" className="space-y-6">
      {Object.entries(groups).map(([section, sectionItems]) => {
        if (sectionItems.length === 0) {
          return null;
        }
        return (
          <div key={section}>
            <p className="mb-2 text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-emerald-200/70">
              {SECTION_LABELS[section] ?? section}
            </p>
            <ul className="space-y-1">
              {sectionItems.map((item) => {
                const active =
                  currentPath === item.href ||
                  (item.href !== "/dashboard" && currentPath.startsWith(item.href));
                return (
                  <li key={item.id}>
                    <Link
                      href={item.href}
                      className={`block rounded-md px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200 ${
                        active ? "bg-white/15 text-white" : "text-emerald-50 hover:bg-white/10"
                      }`}
                      aria-current={active ? "page" : undefined}
                    >
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
