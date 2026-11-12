"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  BarChart,
  DataTable,
  LineChart,
  PieChart,
  SummaryCards,
} from "@/components/reports/SimpleCharts";
import {
  downloadReportExport,
  fetchReportRows,
  fetchReportSummary,
  type ExportFormat,
  type ReportCategory,
} from "@/lib/reportingApi";

type Props = {
  category: ReportCategory;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  title: string;
  description: string;
};

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" ? (v as Record<string, unknown>) : {};
}

export function ReportCategoryPanel({
  category,
  accessToken,
  organisationId,
  role,
  title,
  description,
}: Props) {
  const auth = useMemo(
    () => ({ accessToken, organisationId, role }),
    [accessToken, organisationId, role],
  );
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [status, setStatus] = useState("");
  const [building, setBuilding] = useState("");
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const load = (nextPage = page) => {
    startTransition(async () => {
      setError(null);
      try {
        const filterArgs: Record<string, string | undefined> = {};
        if (createdFrom) filterArgs.created_from = new Date(createdFrom).toISOString();
        if (createdTo) filterArgs.created_to = new Date(createdTo).toISOString();
        if (status) filterArgs.status = status;
        if (building && category === "occupancy") filterArgs.building = building;
        const [sum, table] = await Promise.all([
          fetchReportSummary(category, { ...auth, ...filterArgs }),
          fetchReportRows(category, { ...auth, ...filterArgs, page: nextPage, page_size: 25 }),
        ]);
        setSummary(sum);
        setRows(table.items);
        setTotal(table.total);
        setPage(nextPage);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load report");
        setSummary(null);
        setRows([]);
        setTotal(0);
      }
    });
  };

  useEffect(() => {
    load(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  const cards = useMemo(() => {
    if (!summary) return [];
    const picks: { key: string; label: string }[] = [
      { key: "total", label: "Total" },
      { key: "total_rooms", label: "Rooms" },
      { key: "occupied_rooms", label: "Occupied" },
      { key: "vacant_rooms", label: "Vacant" },
      { key: "occupancy_rate", label: "Occupancy %" },
      { key: "pending_applications", label: "Pending apps" },
      { key: "approved_count", label: "Approved" },
      { key: "rejected_count", label: "Rejected" },
      { key: "overdue_operational", label: "Overdue" },
      { key: "active_assignments", label: "Active cases" },
      { key: "assigned_tenants", label: "Assigned tenants" },
      { key: "overdue_follow_ups", label: "Overdue follow-ups" },
      { key: "open_follow_ups", label: "Open follow-ups" },
      { key: "active_plans", label: "Active plans" },
      { key: "completed_plans", label: "Completed plans" },
      { key: "overdue_reviews", label: "Overdue reviews" },
      { key: "goal_completion_rate", label: "Goal %" },
    ];
    return picks
      .filter((p) => summary[p.key] !== undefined)
      .map((p) => ({ label: p.label, value: summary[p.key] as string | number }));
  }, [summary]);

  const byStatus = useMemo(() => {
    const block = asRecord(summary?.by_status);
    return Object.entries(block).map(([label, value]) => ({ label, value: Number(value) || 0 }));
  }, [summary]);

  const trends = useMemo(() => {
    const raw = Array.isArray(summary?.trends_daily) ? (summary?.trends_daily as Record<string, unknown>[]) : [];
    return raw.map((t) => ({ label: String(t.date ?? ""), value: Number(t.count) || 0 }));
  }, [summary]);

  const byProperty = useMemo(() => {
    const raw = Array.isArray(summary?.by_property)
      ? (summary?.by_property as Record<string, unknown>[])
      : Array.isArray(summary?.trend_comparison)
        ? (summary?.trend_comparison as Record<string, unknown>[])
        : [];
    return raw.map((p) => ({
      label: String(p.property_name ?? p.label ?? p.property_id ?? "Unassigned"),
      value: Number(p.count ?? p.occupied ?? p.occupied_rooms ?? 0) || 0,
    }));
  }, [summary]);

  const onExport = async (format: ExportFormat) => {
    try {
      await downloadReportExport(category, format, {
        ...auth,
        createdFrom: createdFrom ? new Date(createdFrom).toISOString() : undefined,
        createdTo: createdTo ? new Date(createdTo).toISOString() : undefined,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{description}</p>
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label className="text-sm">
          <span className="mb-1 block text-slate-600">From</span>
          <input
            type="date"
            value={createdFrom}
            onChange={(e) => setCreatedFrom(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-slate-600">To</span>
          <input
            type="date"
            value={createdTo}
            onChange={(e) => setCreatedTo(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
        {category !== "occupancy" && category !== "caseload" ? (
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Status</span>
            <input
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              placeholder="optional"
              className="rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
        ) : null}
        {category === "occupancy" ? (
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Building</span>
            <input
              value={building}
              onChange={(e) => setBuilding(e.target.value)}
              placeholder="name / city"
              className="rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
        ) : null}
        <button
          type="button"
          onClick={() => load(1)}
          disabled={pending}
          className="rounded bg-teal-800 px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {pending ? "Loading…" : "Apply filters"}
        </button>
        <div className="ml-auto flex gap-2">
          {(["csv", "pdf", "xlsx"] as ExportFormat[]).map((fmt) => (
            <button
              key={fmt}
              type="button"
              onClick={() => onExport(fmt)}
              className="rounded border border-slate-300 px-3 py-2 text-sm capitalize text-slate-800 hover:bg-slate-50"
            >
              Export {fmt}
            </button>
          ))}
        </div>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {pending && !summary ? <p className="text-sm text-slate-500">Loading report…</p> : null}
      {!pending && summary && cards.length === 0 && rows.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
          No records available for these filters.
        </p>
      ) : null}

      <SummaryCards items={cards} />
      <div className="grid gap-4 lg:grid-cols-2">
        {byStatus.length ? <PieChart title="By status" items={byStatus} /> : null}
        {byProperty.length ? <BarChart title="By property" items={byProperty} /> : null}
        {trends.length ? <LineChart title="Trend over time" points={trends} /> : null}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-slate-800">Detail ({total} rows)</h2>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1 || pending}
              onClick={() => load(page - 1)}
              className="rounded border px-2 py-1 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-sm text-slate-600">Page {page}</span>
            <button
              type="button"
              disabled={page * 25 >= total || pending}
              onClick={() => load(page + 1)}
              className="rounded border px-2 py-1 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
        <DataTable rows={rows} />
      </div>
    </div>
  );
}
