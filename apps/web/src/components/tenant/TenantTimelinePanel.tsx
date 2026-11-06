"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchTenantTimeline, type TimelineItem, type TimelinePage } from "@/lib/tenantTimelineApi";
import { activityBadgeClass } from "@/lib/timelineUi";

type Props = {
  accessToken: string;
  organisationId: string;
  role: string | null | undefined;
  tenantId: string;
  canReadTimeline: boolean;
};

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
      setError(e instanceof Error ? e.message : "Unable to load timeline");
    } finally {
      setLoading(false);
    }
  }, [accessToken, organisationId, role, tenantId, sort, filter, canReadTimeline]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!canReadTimeline) {
    return (
      <section className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Timeline is not available for your current role or permissions.
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-600">Sort</label>
          <select
            className="mt-1 rounded border border-slate-300 px-2 py-1 text-sm"
            value={sort}
            onChange={(e) => setSort(e.target.value as "newest" | "oldest")}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600">Activity type (optional)</label>
          <input
            className="mt-1 rounded border border-slate-300 px-2 py-1 text-sm"
            placeholder="e.g. daily_log, meeting"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <button
          type="button"
          className="rounded-md bg-teal-700 px-3 py-1.5 text-sm text-white"
          onClick={() => void load()}
          disabled={loading}
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error ? (
        <p className="rounded border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>
      ) : null}

      {data && data.items.length === 0 && !loading ? (
        <p className="text-sm text-slate-600">No timeline activities match the current filters.</p>
      ) : null}

      <ul className="space-y-3">
        {(data?.items ?? []).map((item: TimelineItem) => (
          <li key={item.dedupe_key} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded px-2 py-0.5 text-xs font-medium uppercase ${activityBadgeClass(item.activity_type)}`}
              >
                {item.activity_type.replace(/_/g, " ")}
              </span>
              {!item.can_view ? (
                <span className="text-xs text-amber-800">Restricted — open source record with appropriate access</span>
              ) : null}
            </div>
            <p className="mt-2 font-medium text-forest-900">{item.title}</p>
            {item.summary ? <p className="text-sm text-slate-600">{item.summary}</p> : null}
            <p className="mt-1 text-xs text-slate-500">
              {new Date(item.occurred_at).toLocaleString()}
              {item.status ? ` · ${item.status}` : ""}
              {item.reference ? ` · ${item.reference}` : ""}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
