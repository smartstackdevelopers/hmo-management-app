"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createInspection,
  createRentRecord,
  fetchInspections,
  fetchLandlordDashboard,
  fetchPortfolio,
  fetchRentRecords,
  fetchRepairs,
  updateRentStatus,
  type LandlordDashboard,
} from "@/lib/landlordEnterpriseApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-forest-900">{value}</p>
    </div>
  );
}

export function LandlordEnterpriseClient({ accessToken, organisationId, role }: Props) {
  const opts = useMemo(
    () => ({ accessToken, organisationId, role }),
    [accessToken, organisationId, role],
  );
  const [dash, setDash] = useState<LandlordDashboard | null>(null);
  const [portfolio, setPortfolio] = useState<Array<Record<string, unknown>>>([]);
  const [rents, setRents] = useState<Array<Record<string, unknown>>>([]);
  const [inspections, setInspections] = useState<Array<Record<string, unknown>>>([]);
  const [repairs, setRepairs] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [building, setBuilding] = useState("");
  const [rentAmount, setRentAmount] = useState("450.00");
  const [rentPropertyId, setRentPropertyId] = useState("");
  const [inspectionTitle, setInspectionTitle] = useState("Routine inspection");
  const [inspectionPropertyId, setInspectionPropertyId] = useState("");
  const [inspectionDate, setInspectionDate] = useState(() => new Date().toISOString().slice(0, 10));

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [d, p, r, i, rep] = await Promise.all([
        fetchLandlordDashboard(opts),
        fetchPortfolio({ ...opts, query: { building: building || undefined } }),
        fetchRentRecords(opts),
        fetchInspections(opts),
        fetchRepairs(opts),
      ]);
      setDash(d);
      setPortfolio(p.items);
      setRents(r.items);
      setInspections(i.items);
      setRepairs(rep.items);
      if (!rentPropertyId && d.properties[0]) setRentPropertyId(d.properties[0].id);
      if (!inspectionPropertyId && d.properties[0]) setInspectionPropertyId(d.properties[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load landlord enterprise data");
    } finally {
      setLoading(false);
    }
  }, [opts, building, rentPropertyId, inspectionPropertyId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onCreateRent() {
    setMessage(null);
    try {
      const today = new Date();
      const start = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
      await createRentRecord({
        ...opts,
        body: {
          property_id: rentPropertyId,
          amount: rentAmount,
          period_start: start,
          period_end: today.toISOString().slice(0, 10),
          status: "due",
        },
      });
      setMessage("Rent record created.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create rent record");
    }
  }

  async function onMarkPaid(rentId: string) {
    setMessage(null);
    try {
      await updateRentStatus({
        ...opts,
        rentId,
        body: { status: "recorded_paid", recorded_paid_note: "Payment recorded by authorised landlord action" },
      });
      setMessage("Rent marked as recorded paid.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update rent status");
    }
  }

  async function onCreateInspection() {
    setMessage(null);
    try {
      await createInspection({
        ...opts,
        body: {
          property_id: inspectionPropertyId,
          title: inspectionTitle,
          scheduled_date: inspectionDate,
          status: "scheduled",
        },
      });
      setMessage("Inspection created.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create inspection");
    }
  }

  if (loading && !dash) {
    return <p className="text-sm text-slate-600">Loading landlord enterprise dashboard…</p>;
  }
  if (error && !dash) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
        {error}
        <button type="button" className="ml-3 underline" onClick={() => void reload()}>
          Retry
        </button>
      </div>
    );
  }
  if (!dash) {
    return <p className="text-sm text-slate-600">No landlord data available for this organisation.</p>;
  }

  return (
    <div className="space-y-8">
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {message ? <p className="text-sm text-teal-800">{message}</p> : null}
      <p className="text-sm text-slate-600">{dash.ledger_disclaimer}</p>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Properties" value={dash.total_properties} />
        <StatCard label="Rooms" value={dash.total_rooms} />
        <StatCard label="Occupied" value={dash.occupied_rooms} />
        <StatCard label="Vacant" value={dash.vacant_rooms} />
        <StatCard label="Active tenancies" value={dash.active_tenancies} />
        <StatCard label="Rent outstanding" value={dash.rent.outstanding + dash.rent.due} />
        <StatCard label="Inspections overdue" value={dash.inspections.overdue} />
        <StatCard label="Open repairs" value={dash.repairs.open} />
      </section>

      <nav className="flex flex-wrap gap-3 text-sm">
        <Link className="text-teal-800 underline" href="/dashboard/landlord#portfolio">
          Portfolio
        </Link>
        <Link className="text-teal-800 underline" href="/dashboard/landlord#rent">
          Rent ledger
        </Link>
        <Link className="text-teal-800 underline" href="/dashboard/landlord#inspections">
          Inspections
        </Link>
        <Link className="text-teal-800 underline" href="/dashboard/landlord#repairs">
          Repairs
        </Link>
        <Link className="text-teal-800 underline" href="/properties">
          Properties API
        </Link>
      </nav>

      <section id="portfolio" className="space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <h2 className="text-lg font-semibold text-forest-900">Portfolio analytics</h2>
          <input
            className="rounded border border-slate-300 px-3 py-2 text-sm"
            placeholder="Filter by building / city"
            value={building}
            onChange={(e) => setBuilding(e.target.value)}
          />
          <button
            type="button"
            className="rounded bg-teal-800 px-3 py-2 text-sm text-white"
            onClick={() => void reload()}
          >
            Apply
          </button>
        </div>
        {portfolio.length === 0 ? (
          <p className="text-sm text-slate-600">No properties match these filters.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2">Property</th>
                  <th className="px-3 py-2">Rooms</th>
                  <th className="px-3 py-2">Occupied</th>
                  <th className="px-3 py-2">Vacant</th>
                  <th className="px-3 py-2">Occupancy %</th>
                  <th className="px-3 py-2">Repairs</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.map((row) => (
                  <tr key={String(row.property_id)} className="border-t border-slate-100">
                    <td className="px-3 py-2">{String(row.property_name)}</td>
                    <td className="px-3 py-2">{String(row.total_rooms)}</td>
                    <td className="px-3 py-2">{String(row.occupied_rooms)}</td>
                    <td className="px-3 py-2">{String(row.vacant_rooms)}</td>
                    <td className="px-3 py-2">{String(row.occupancy_rate)}</td>
                    <td className="px-3 py-2">{String(row.outstanding_repairs)}</td>
                    <td className="px-3 py-2">{String(row.maintenance_status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section id="rent" className="space-y-3">
        <h2 className="text-lg font-semibold text-forest-900">Rent records ledger</h2>
        <div className="flex flex-wrap gap-2">
          <select
            className="rounded border border-slate-300 px-3 py-2 text-sm"
            value={rentPropertyId}
            onChange={(e) => setRentPropertyId(e.target.value)}
          >
            {dash.properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <input
            className="rounded border border-slate-300 px-3 py-2 text-sm"
            value={rentAmount}
            onChange={(e) => setRentAmount(e.target.value)}
            aria-label="Rent amount"
          />
          <button type="button" className="rounded bg-teal-800 px-3 py-2 text-sm text-white" onClick={() => void onCreateRent()}>
            Add rent record
          </button>
        </div>
        {rents.length === 0 ? (
          <p className="text-sm text-slate-600">No rent records yet.</p>
        ) : (
          <ul className="space-y-2">
            {rents.map((row) => (
              <li key={String(row.id)} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
                <p className="font-medium text-forest-900">
                  {String(row.property_name)} · £{String(row.amount)} · {String(row.status)}
                </p>
                <p className="text-slate-600">
                  {String(row.period_start)} → {String(row.period_end)}
                  {row.tenancy_reference ? ` · ${String(row.tenancy_reference)}` : ""}
                </p>
                {row.status !== "recorded_paid" ? (
                  <button
                    type="button"
                    className="mt-2 text-teal-800 underline"
                    onClick={() => void onMarkPaid(String(row.id))}
                  >
                    Record as paid (authorised note)
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section id="inspections" className="space-y-3">
        <h2 className="text-lg font-semibold text-forest-900">Inspections</h2>
        <div className="flex flex-wrap gap-2">
          <select
            className="rounded border border-slate-300 px-3 py-2 text-sm"
            value={inspectionPropertyId}
            onChange={(e) => setInspectionPropertyId(e.target.value)}
          >
            {dash.properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <input
            className="rounded border border-slate-300 px-3 py-2 text-sm"
            value={inspectionTitle}
            onChange={(e) => setInspectionTitle(e.target.value)}
          />
          <input
            type="date"
            className="rounded border border-slate-300 px-3 py-2 text-sm"
            value={inspectionDate}
            onChange={(e) => setInspectionDate(e.target.value)}
          />
          <button
            type="button"
            className="rounded bg-teal-800 px-3 py-2 text-sm text-white"
            onClick={() => void onCreateInspection()}
          >
            Schedule inspection
          </button>
        </div>
        <p className="text-sm text-slate-600">
          Upcoming: {dash.inspections.upcoming} · Overdue: {dash.inspections.overdue} · Completed:{" "}
          {dash.inspections.completed}
        </p>
        {inspections.length === 0 ? (
          <p className="text-sm text-slate-600">No inspections yet.</p>
        ) : (
          <ul className="space-y-2">
            {inspections.map((row) => (
              <li key={String(row.id)} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
                <p className="font-medium text-forest-900">
                  {String(row.title)} · {String(row.effective_status)}
                </p>
                <p className="text-slate-600">
                  {String(row.property_name)} · {String(row.scheduled_date)}
                </p>
                {row.findings ? <p className="mt-1 text-slate-700">Findings: {String(row.findings)}</p> : null}
                {row.follow_up_actions ? (
                  <p className="text-slate-700">Follow-up: {String(row.follow_up_actions)}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section id="repairs" className="space-y-3">
        <h2 className="text-lg font-semibold text-forest-900">Repair oversight</h2>
        <p className="text-sm text-slate-600">
          Open: {dash.repairs.open} · Completed: {dash.repairs.completed} · Pending maintenance:{" "}
          {dash.repairs.pending_maintenance}
        </p>
        {repairs.length === 0 ? (
          <p className="text-sm text-slate-600">No repairs on your properties.</p>
        ) : (
          <ul className="space-y-2">
            {repairs.map((row) => (
              <li key={String(row.id)} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
                <p className="font-medium text-forest-900">
                  {String(row.title)} · {String(row.priority)} · {String(row.status)}
                  {row.is_overdue ? " · overdue" : ""}
                </p>
                <p className="text-slate-600">
                  {String(row.property_name)}
                  {row.scheduled_visit_at ? ` · scheduled ${String(row.scheduled_visit_at)}` : ""}
                </p>
                {row.completion_notes ? (
                  <p className="mt-1 text-slate-700">Completion: {String(row.completion_notes)}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
