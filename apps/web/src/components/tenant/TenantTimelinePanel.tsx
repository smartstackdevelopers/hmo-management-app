"use client";

import { useCallback, useEffect, useState } from "react";
import { btnSecondary, humanize, inputClass, labelClass, StatusChip } from "@/components/ui/primitives";
import { fetchTenantTimeline, type TimelineItem, type TimelinePage } from "@/lib/tenantTimelineApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role: string | null | undefined;
  tenantId: string;
  canReadTimeline: boolean;
};

const ACTIVITY_TYPES = [
  "daily_log",
  "handover",
  "tenant_visit",
  "meeting",
  "appointment",
  "tenant_follow_up",
  "complaint",
  "maintenance",
];

export function TenantTimelinePanel({
  accessToken,
  organisationId,
  role,
  tenantId,
  canReadTimeline,
}: Props) {
  const [data, setData] = useState<TimelinePage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const [filter, setFilter] = useState<string>("");

  const load = useCallback(async () => {
    if (!canReadTimeline) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const types = filter.trim() ? [filter.trim()] : undefined;
      const page = await fetchTenantTimeline({
        accessToken,
        organisationId,
        role,
        tenantId,
        page: 1,
        pageSize: 50,
        sort,
        activityType: types,
      });
      setData(page);
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "We couldn't load the timeline. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [accessToken, organisationId, role, tenantId, sort, filter, canReadTimeline]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!canReadTimeline) {
    return (
      <p className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        The activity timeline isn&apos;t available with your current access.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1.5">
          <label htmlFor="timeline-sort" className={labelClass}>
            Sort
          </label>
          <select
            id="timeline-sort"
            className={`${inputClass} w-auto`}
            value={sort}
            onChange={(e) => setSort(e.target.value as "newest" | "oldest")}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="timeline-type" className={labelClass}>
            Activity type
          </label>
          <select id="timeline-type" className={`${inputClass} w-auto`} value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All activity</option>
            {ACTIVITY_TYPES.map((type) => (
              <option key={type} value={type}>
                {humanize(type)}
              </option>
            ))}
          </select>
        </div>
        <button type="button" className={btnSecondary} onClick={() => void load()} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      {data && data.items.length === 0 && !loading ? (
        <p className="text-sm text-slate-500">No activity matches these filters yet.</p>
      ) : null}

      <ol className="relative space-y-5 border-l border-slate-200 pl-6">
        {(data?.items ?? []).map((item: TimelineItem) => (
          <li key={item.dedupe_key} className="relative">
            <span
              aria-hidden="true"
              className="absolute -left-[1.85rem] top-1.5 h-3 w-3 rounded-full border-2 border-white bg-brand-600 ring-1 ring-brand-200"
            />
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone="blue">{humanize(item.activity_type)}</StatusChip>
              {item.status ? <StatusChip status={item.status} /> : null}
              <span className="ml-auto text-xs text-slate-500">
                {new Date(item.occurred_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}
              </span>
            </div>
            <p className="mt-1.5 text-sm font-semibold text-slate-900">{item.title}</p>
            {item.summary ? <p className="mt-0.5 text-sm text-slate-600">{item.summary}</p> : null}
            {item.reference ? <p className="mt-0.5 text-xs text-slate-500">Ref {item.reference}</p> : null}
            {!item.can_view ? (
              <p className="mt-1 text-xs text-amber-700">Restricted — open the original record if you have access.</p>
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  );
}
