"use client";

import { useState } from "react";
import Link from "next/link";
import type { NavItem } from "@/lib/navigation";

type MobileNavProps = {
  items: NavItem[];
  brand: string;
};

export function MobileNav({ items, brand }: MobileNavProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="md:hidden">
      <div className="flex items-center justify-between gap-3 bg-forest-900 px-4 py-3 text-white">
        <p className="text-sm font-semibold">{brand}</p>
        <button
          type="button"
          className="min-h-11 min-w-11 rounded-md bg-white/10 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200"
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
          className="space-y-1 border-b border-forest-800 bg-forest-900 px-4 py-3 text-emerald-50"
        >
          {items.map((item) => (
            <Link
              key={item.id}
              href={item.href}
              className="block min-h-11 rounded-md px-3 py-2 text-sm hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200"
              onClick={() => setOpen(false)}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </div>
  );
}
