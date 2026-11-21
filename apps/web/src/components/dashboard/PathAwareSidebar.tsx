"use client";

import { usePathname } from "next/navigation";
import { SidebarNav } from "@/components/dashboard/SidebarNav";
import type { NavItem } from "@/lib/navigation";

export function PathAwareSidebar({ items, role = null }: { items: NavItem[]; role?: string | null }) {
  const pathname = usePathname() ?? "/dashboard";
  return <SidebarNav items={items} currentPath={pathname} role={role} />;
}
