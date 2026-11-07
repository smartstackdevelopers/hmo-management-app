import type { ReactNode } from "react";
import Link from "next/link";

const links = [
  { href: "/dashboard/communications", label: "Dashboard" },
  { href: "/dashboard/communications/inbox", label: "Inbox" },
  { href: "/dashboard/communications/sent", label: "Sent" },
  { href: "/dashboard/communications/deliveries", label: "Deliveries" },
  { href: "/dashboard/communications/reminders", label: "Reminders" },
  { href: "/dashboard/communications/preferences", label: "Preferences" },
  { href: "/dashboard/communications/announcements", label: "Announcements" },
  { href: "/dashboard/communications/templates", label: "Templates" },
  { href: "/dashboard/communications/translations", label: "Translations" },
];

export default function CommunicationsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <nav className="flex flex-wrap gap-2 text-sm">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="rounded border border-slate-300 px-3 py-1.5 hover:bg-slate-50"
          >
            {l.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}
