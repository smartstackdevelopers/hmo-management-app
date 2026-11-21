"use client";

import { useMemo, useState } from "react";
import type { PlatformOrganisation } from "@/lib/platformGovernanceApi";
import { Avatar, DataTable, StatusChip, Td, Th, humanize, inputClass } from "@/components/ui/primitives";

type Props = {
  organisations: PlatformOrganisation[];
};

export function OrganisationsTable({ organisations }: Props) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");

  const statuses = useMemo(() => {
    const found = Array.from(new Set(organisations.map((org) => org.status).filter(Boolean)));
    return ["all", ...found];
  }, [organisations]);

  const filtered = organisations.filter((org) => {
    const q = query.trim().toLowerCase();
    const matchesQuery = !q || org.name.toLowerCase().includes(q) || org.slug.toLowerCase().includes(q);
    const matchesStatus = status === "all" || org.status === status;
    return matchesQuery && matchesStatus;
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <label className="block min-w-0 flex-1 lg:max-w-md">
          <span className="sr-only">Search organisations</span>
          <input
            className={inputClass}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search organisations"
          />
        </label>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Organisation status">
          {statuses.map((value) => {
            const active = value === status;
            const count = value === "all" ? organisations.length : organisations.filter((org) => org.status === value).length;
            return (
              <button
                key={value}
                type="button"
                aria-pressed={active}
                onClick={() => setStatus(value)}
                className={`inline-flex h-8 items-center gap-1.5 rounded-full px-3.5 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
                  active ? "bg-brand-700 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {value === "all" ? "All" : humanize(value)}
                <span className={`text-xs ${active ? "text-brand-100" : "text-slate-400"}`}>{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
          No organisations match this search.
        </p>
      ) : (
        <DataTable caption="Platform organisations">
          <thead>
            <tr>
              <Th>Organisation</Th>
              <Th>Slug</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((org) => (
              <tr key={org.id}>
                <Td>
                  <span className="flex items-center gap-3">
                    <Avatar name={org.name} size="sm" />
                    <span className="font-semibold text-slate-900">{org.name}</span>
                  </span>
                </Td>
                <Td className="font-mono text-xs text-slate-500">{org.slug}</Td>
                <Td>
                  <StatusChip status={org.status} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {filtered.length === 0 ? "0" : `1–${filtered.length}`} of {organisations.length}
      </p>
    </div>
  );
}
