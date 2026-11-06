"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { CaseAssignment } from "@/lib/supportApi";

export function CaseloadClient({
  initialItems,
  total,
  initialQuery,
}: {
  initialItems: CaseAssignment[];
  total: number;
  initialQuery: string;
}) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  return (
    <div className="space-y-4">
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          const params = new URLSearchParams();
          if (query.trim()) {
            params.set("q", query.trim());
          }
          router.push(`/dashboard/support-worker?${params.toString()}`);
        }}
      >
        <label className="sr-only" htmlFor="caseload-search">
          Search caseload
        </label>
        <input
          id="caseload-search"
          className="min-w-[16rem] flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by name or tenancy reference"
        />
        <button
          type="submit"
          className="rounded-md bg-forest-900 px-4 py-2 text-sm text-white hover:bg-forest-800"
        >
          Search
        </button>
      </form>

      <p className="text-sm text-slate-600">{total} assigned case{total === 1 ? "" : "s"}</p>

      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {initialItems.map((item) => (
          <li key={item.id} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium text-forest-900">
                {item.tenant_preferred_name || item.tenant_full_name || "Tenant"}
              </p>
              <p className="text-sm text-slate-600">
                Assigned {new Date(item.assigned_at).toLocaleDateString()} · status {item.status}
              </p>
              <p className="text-xs text-slate-500">
                Logs: {item.recent_log_count ?? 0} · Pending handovers:{" "}
                {item.pending_handover_count ?? 0}
              </p>
            </div>
            <Link
              href={`/dashboard/caseload/${item.tenant_id}`}
              className="rounded-md border border-teal-700 px-3 py-2 text-sm text-teal-800 hover:bg-teal-50"
            >
              Open case
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
