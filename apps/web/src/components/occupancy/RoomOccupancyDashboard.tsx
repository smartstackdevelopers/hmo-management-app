"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  correctOccupancyCount,
  fetchOccupancyAlerts,
  fetchOccupancyDashboard,
  fetchOccupancyRooms,
  fetchOccupancyUsage,
  updateApprovalGate,
} from "@/lib/roomOccupancyApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
  canCorrect: boolean;
};

const STATUSES = ["available", "occupied", "near_capacity", "at_capacity", "offline"] as const;

export function RoomOccupancyDashboard({
  accessToken,
  organisationId,
  role,
  canManage,
  canCorrect,
}: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [rooms, setRooms] = useState<Record<string, unknown>[]>([]);
  const [alerts, setAlerts] = useState<Record<string, unknown>[]>([]);
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [statusFilter, setStatusFilter] = useState("");
  const [floorFilter, setFloorFilter] = useState("");

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        const [d, r, a, u] = await Promise.all([
          fetchOccupancyDashboard(auth),
          fetchOccupancyRooms({
            ...auth,
            status: statusFilter || undefined,
            floor: floorFilter || undefined,
          }),
          fetchOccupancyAlerts(auth),
          fetchOccupancyUsage(auth, "daily"),
        ]);
        setDash(d);
        setRooms(r.items);
        setAlerts(a.items);
        setUsage(u);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load room occupancy");
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, floorFilter]);

  const gate = (dash?.approval_gate ?? null) as Record<string, unknown> | null;
  const liveActive = Boolean(dash?.live_counting_active);
  const statusCounts = (dash?.status_counts ?? {}) as Record<string, number>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Room occupancy</h1>
        <p className="mt-1 text-sm text-slate-600">
          Estimated people counts only. No facial recognition, identity tracking, or raw video by
          default. Live camera activation stays disabled until the privacy approval gate is complete.
        </p>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {pending && !dash ? <p className="text-sm text-slate-500">Loading…</p> : null}

      <section className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <h2 className="text-sm font-medium text-amber-950">Privacy approval gate</h2>
        {!gate ? (
          <p className="text-sm text-amber-900">Loading gate status…</p>
        ) : (
          <>
            <p className="text-sm text-amber-900">
              Gate complete: {String(gate.gate_complete)} · Live counting active: {String(liveActive)}
            </p>
            <ul className="grid gap-1 text-xs text-amber-900 sm:grid-cols-2">
              {(
                [
                  ["feasibility_status", "Feasibility"],
                  ["dpia_status", "DPIA"],
                  ["signage_status", "Signage"],
                  ["retention_policy_status", "Retention"],
                  ["camera_compatibility_status", "Camera compatibility"],
                ] as const
              ).map(([key, label]) => (
                <li key={key}>
                  {label}: <strong>{String(gate[key])}</strong>
                </li>
              ))}
            </ul>
            {Array.isArray(gate.outstanding_requirements) && gate.outstanding_requirements.length > 0 ? (
              <p className="text-sm text-amber-900">
                Outstanding: {(gate.outstanding_requirements as string[]).join(", ")}
              </p>
            ) : null}
            {!liveActive ? (
              <p className="text-sm font-medium text-amber-950">
                Live RTSP/camera collection is disabled. Register devices in pending state only until
                approvals are recorded.
              </p>
            ) : null}
            {canManage ? (
              <p className="text-xs text-amber-800">
                Use the API or admin controls to update gate statuses. Statuses are never auto-approved.
              </p>
            ) : null}
          </>
        )}
      </section>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {STATUSES.map((s) => (
          <div key={s} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-slate-500">{s.replace("_", " ")}</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{statusCounts[s] ?? 0}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          className="rounded border px-2 py-1.5 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          className="rounded border px-2 py-1.5 text-sm"
          placeholder="Floor label"
          value={floorFilter}
          onChange={(e) => setFloorFilter(e.target.value)}
        />
        <button type="button" className="rounded border px-3 py-1.5 text-sm" onClick={refresh}>
          Refresh
        </button>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Rooms</h2>
        {!rooms.length ? (
          <p className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
            No occupancy states yet. After devices are registered and the approval gate enables live
            counting, edge counts will appear here. Offline rooms never show as zero occupants.
          </p>
        ) : (
          <ul className="space-y-2">
            {rooms.map((room) => (
              <li key={String(room.id)} className="rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="font-medium text-slate-900">
                      {String(room.property_name ?? "Property")} · {String(room.room_label ?? room.room_id)}
                    </div>
                    <div className="text-slate-600">
                      Floor {String(room.floor ?? "—")} · status {String(room.occupancy_status)} · device{" "}
                      {String(room.device_connection_status)}
                    </div>
                    <div className="text-xs text-slate-500">
                      {String(room.estimated_count_label)}:{" "}
                      {room.occupancy_status === "offline" ? "—" : String(room.estimated_count ?? "—")} /{" "}
                      {String(room.max_capacity)}
                      {room.occupancy_percent != null ? ` (${String(room.occupancy_percent)}%)` : ""}
                      {room.is_manual_correction ? " · manually corrected" : ""} · updated{" "}
                      {String(room.last_updated_at ?? "—")}
                    </div>
                  </div>
                  {canCorrect && room.occupancy_status !== "offline" ? (
                    <button
                      type="button"
                      className="rounded border px-2 py-1"
                      onClick={() =>
                        startTransition(async () => {
                          const raw = window.prompt("Corrected estimated count", String(room.estimated_count ?? 0));
                          if (raw == null) return;
                          const reason = window.prompt("Reason for correction");
                          if (!reason) return;
                          try {
                            await correctOccupancyCount(auth, String(room.room_id), {
                              corrected_count: Number(raw),
                              reason,
                            });
                            refresh();
                          } catch (e) {
                            setError(e instanceof Error ? e.message : "Correction failed");
                          }
                        })
                      }
                    >
                      Correct count
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Active alerts</h2>
        {!alerts.length ? (
          <p className="text-sm text-slate-500">No active occupancy alerts.</p>
        ) : (
          <ul className="space-y-2">
            {alerts.map((a) => (
              <li key={String(a.id)} className="rounded border bg-white p-3 text-sm">
                {String(a.alert_category)} · {String(a.severity)} · {String(a.message)}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Usage summary (daily)</h2>
        {usage ? (
          <div className="text-sm text-slate-700">
            Peak {String(usage.peak_occupancy)} · samples {String(usage.sample_count)}
            <p className="text-xs text-slate-500">{String(usage.note)}</p>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No history yet.</p>
        )}
      </section>

      {canManage ? (
        <section className="rounded border border-slate-200 bg-white p-4 text-sm">
          <h2 className="font-medium text-slate-800">Admin note</h2>
          <p className="mt-1 text-slate-600">
            Marking DPIA/feasibility approved requires an authorised administrator to set those statuses
            explicitly via the approval-gate API after real organisational approval. This UI does not
            invent approvals.
          </p>
          <button
            type="button"
            className="mt-3 rounded border px-3 py-1.5"
            onClick={() =>
              startTransition(async () => {
                try {
                  await updateApprovalGate(auth, { notes: "Reviewed outstanding requirements in dashboard" });
                  refresh();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Gate update failed");
                }
              })
            }
          >
            Save review note
          </button>
        </section>
      ) : null}
    </div>
  );
}
