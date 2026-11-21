"use client";

import { usePathname } from "next/navigation";
import { FilterTabs } from "@/components/ui/primitives";

const LINKS = [
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

export function CommunicationsNav() {
  const path = usePathname();
  return (
    <FilterTabs
      tabs={LINKS.map((link) => ({
        ...link,
        active: link.href === "/dashboard/communications" ? path === link.href : path.startsWith(link.href),
      }))}
    />
  );
}
