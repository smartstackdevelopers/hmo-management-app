"use client";

import { usePathname } from "next/navigation";
import { SidebarNav } from "@/components/dashboard/SidebarNav";
import type { NavItem } from "@/lib/navigation";

export function PathAwareSidebar({ items }: { items: NavItem[] }) {
  const pathname = usePathname() ?? "/dashboard";
  return <SidebarNav items={items} currentPath={pathname} />;
}
