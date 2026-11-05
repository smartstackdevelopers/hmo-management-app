import type { ReactNode } from "react";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { getDashboardSession } from "@/lib/session";

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const session = await getDashboardSession();
  return <DashboardShell session={session}>{children}</DashboardShell>;
}
