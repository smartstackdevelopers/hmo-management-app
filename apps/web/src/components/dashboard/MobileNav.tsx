"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark } from "@/components/brand/BrandMark";
import { groupNavItemsByArea, isNavItemActive, type NavItem } from "@/lib/navigation";

type MobileNavProps = {
  items: NavItem[];
  brand: string;
};

export function MobileNav({ items, brand, role = null }: MobileNavProps & { role?: string | null }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname() ?? "";
  const areas = groupNavItemsByArea(items, role);

  return (
    <div className="sticky top-0 z-30 md:hidden">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <BrandMark size="sm" />
          <span className="text-base font-bold text-navy-900">{brand}</span>
        </Link>
        <button
          type="button"
          className="min-h-11 min-w-11 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          aria-expanded={open}
          aria-controls="mobile-dashboard-nav"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Close menu" : "Menu"}
        </button>
      </div>
      {open ? (
        <nav
          id="mobile-dashboard-nav"
          aria-label="Mobile dashboard"
          className="max-h-[75vh] space-y-4 overflow-y-auto border-b border-slate-200 bg-white px-4 py-4 shadow-lift"
        >
          {areas.map((area) => (
            <div key={area.id}>
              <p className="px-3 pb-1 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-slate-400">
                {area.label}
              </p>
              {area.items.map((item) => {
                const active = isNavItemActive(item, pathname);
                return (
                  <Link
                    key={item.id}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex min-h-11 items-center rounded-lg px-3 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
                      active ? "bg-brand-50 font-semibold text-brand-700" : "text-slate-700 hover:bg-slate-50"
                    }`}
                    onClick={() => setOpen(false)}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      ) : null}
    </div>
  );
}
