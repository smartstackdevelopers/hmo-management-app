"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Avatar, btnSecondary, DataTable, inputClass, linkClass, StatusChip, Td, Th } from "@/components/ui/primitives";
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
        className="flex flex-wrap items-center gap-2"
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
          className={`${inputClass} min-w-[16rem] flex-1`}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by name or tenancy reference"
        />
        <button type="submit" className={btnSecondary}>
          Search
        </button>
      </form>

      <p className="text-sm text-slate-500">
        {initialItems.length === 0 ? `Showing 0 of ${total}` : `Showing 1–${initialItems.length} of ${total}`}
      </p>

      {initialItems.length > 0 ? (
        <DataTable caption="Assigned cases">
          <thead>
            <tr>
              <Th>Tenant</Th>
              <Th>Assigned</Th>
              <Th>Status</Th>
              <Th className="text-right">Logs</Th>
              <Th className="text-right">Pending handovers</Th>
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {initialItems.map((item) => {
              const name = item.tenant_preferred_name || item.tenant_full_name || "";
              return (
                <tr key={item.id} className="hover:bg-slate-50/60">
                  <Td>
                    <div className="flex items-center gap-3">
                      <Avatar name={name || "?"} size="sm" />
                      <span className="font-semibold text-slate-900">{name || "—"}</span>
                    </div>
                  </Td>
                  <Td>{new Date(item.assigned_at).toLocaleDateString("en-GB")}</Td>
                  <Td>
                    <StatusChip status={item.status} />
                  </Td>
                  <Td className="text-right tabular-nums">{item.recent_log_count ?? 0}</Td>
                  <Td className="text-right tabular-nums">{item.pending_handover_count ?? 0}</Td>
                  <Td className="text-right">
                    <Link href={`/dashboard/caseload/${item.tenant_id}`} className={linkClass}>
                      Open case
                    </Link>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      ) : null}
    </div>
  );
}
