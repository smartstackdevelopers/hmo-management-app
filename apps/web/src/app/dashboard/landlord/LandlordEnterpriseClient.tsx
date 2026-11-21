"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import {
  btnPrimary,
  btnSecondary,
  Card,
  CardHeader,
  DataTable,
  inputClass,
  linkClass,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
} from "@/components/ui/primitives";
import {
  archiveRentRecord,
  createInspection,
  createRentRecord,
  fetchInspections,
  fetchLandlordDashboard,
  fetchPortfolio,
  fetchRentRecords,
  fetchRepairs,
  updateInspection,
  updateRentStatus,
  type LandlordDashboard,
} from "@/lib/landlordEnterpriseApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

export function LandlordEnterpriseClient({ accessToken, organisationId, role }: Props) {
  // Only landlords receive rent_records.manage / inspections.manage in the RBAC matrix.
  // Org admins may oversee portfolio/repairs via properties.*; API still enforces writes.
  const canManageLedger = role === "landlord";
  const opts = useMemo(
    () => ({ accessToken, organisationId, role }),
    [accessToken, organisationId, role],
  );
  const [dash, setDash] = useState<LandlordDashboard | null>(null);
  const [portfolio, setPortfolio] = useState<Array<Record<string, unknown>>>([]);
  const [vacancyTrend, setVacancyTrend] = useState<Array<Record<string, unknown>>>([]);
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
      setVacancyTrend(p.vacancy_trend ?? []);
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

  async function onArchiveRent(rentId: string) {
    setMessage(null);
    try {
      await archiveRentRecord({ ...opts, rentId });
      setMessage("Rent record archived.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not archive rent record");
    }
  }

  async function onCompleteInspection(row: Record<string, unknown>) {
    setMessage(null);
    try {
      const today = new Date().toISOString().slice(0, 10);
      await updateInspection({
        ...opts,
        inspectionId: String(row.id),
        body: {
          property_id: row.property_id,
          room_id: row.room_id ?? null,
          title: row.title,
          scheduled_date: row.scheduled_date,
          completed_date: today,
          status: "completed",
          findings: row.findings ?? "Completed via landlord enterprise dashboard",
          follow_up_actions: row.follow_up_actions ?? null,
        },
      });
      setMessage("Inspection marked completed.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update inspection");
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
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {message ? <p className="text-sm font-medium text-brand-800">{message}</p> : null}
      <p className="text-sm text-slate-600">{dash.ledger_disclaimer}</p>

      <StatGrid>
        <StatCard label="Properties" value={dash.total_properties} />
        <StatCard label="Rooms" value={dash.total_rooms} />
        <StatCard label="Occupied" value={dash.occupied_rooms} tone="green" />
        <StatCard label="Vacant" value={dash.vacant_rooms} tone={dash.vacant_rooms > 0 ? "amber" : "gray"} />
        <StatCard label="Active tenancies" value={dash.active_tenancies} />
        <StatCard label="Rent outstanding" value={dash.rent.outstanding + dash.rent.due} tone="amber" />
        <StatCard
          label="Inspections overdue"
          value={dash.inspections.overdue}
          tone={dash.inspections.overdue > 0 ? "red" : "gray"}
          hint={dash.inspections.overdue > 0 ? "Overdue" : undefined}
        />
        <StatCard label="Open repairs" value={dash.repairs.open} />
      </StatGrid>

      <nav aria-label="Landlord sections" className="flex flex-wrap gap-2">
        <Link className={linkClass} href="/dashboard/landlord#portfolio">
          Portfolio
        </Link>
        <Link className={linkClass} href="/dashboard/landlord#rent">
          Rent ledger
        </Link>
        <Link className={linkClass} href="/dashboard/landlord#inspections">
          Inspections
        </Link>
        <Link className={linkClass} href="/dashboard/landlord#repairs">
          Repairs
        </Link>
        <Link className={linkClass} href="/properties">
          Properties
        </Link>
      </nav>

      <section id="portfolio" className="space-y-4">
        <CardHeader title="Portfolio analytics" description="Occupancy and repair load for properties you can see." />
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-[220px] flex-1">
            <label htmlFor="portfolio-building" className="sr-only">
              Filter by building or city
            </label>
            <input
              id="portfolio-building"
              className={inputClass}
              placeholder="Filter by building or city"
              value={building}
              onChange={(e) => setBuilding(e.target.value)}
            />
          </div>
          <button type="button" className={btnPrimary} onClick={() => void reload()}>
            Apply
          </button>
        </div>
        {portfolio.length === 0 ? (
          <EmptyState title="No properties" description="No properties match these filters." />
        ) : (
          <DataTable caption="Portfolio">
            <thead>
              <tr>
                <Th>Property</Th>
                <Th>Rooms</Th>
                <Th>Occupied</Th>
                <Th>Vacant</Th>
                <Th>Occupancy %</Th>
                <Th>Repairs</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {portfolio.map((row) => (
                <tr key={String(row.property_id)} className="hover:bg-slate-50">
                  <Td className="font-semibold text-slate-900">{String(row.property_name)}</Td>
                  <Td>{String(row.total_rooms)}</Td>
                  <Td>{String(row.occupied_rooms)}</Td>
                  <Td>{String(row.vacant_rooms)}</Td>
                  <Td>{String(row.occupancy_rate)}</Td>
                  <Td>{String(row.outstanding_repairs)}</Td>
                  <Td>
                    <StatusChip status={String(row.maintenance_status)} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        {vacancyTrend.length > 0 ? (
          <Card>
            <CardHeader title="Vacancy trend" />
            <ul className="space-y-1 text-sm text-slate-600">
              {vacancyTrend.map((point, idx) => (
                <li key={`${String(point.period ?? idx)}-${idx}`}>
                  {String(point.period ?? point.label ?? `Point ${idx + 1}`)}: vacant{" "}
                  {String(point.vacant_rooms ?? point.vacant ?? "—")} / rooms{" "}
                  {String(point.total_rooms ?? point.rooms ?? "—")}
                </li>
              ))}
            </ul>
          </Card>
        ) : null}
      </section>

      <section id="rent" className="space-y-4">
        <CardHeader title="Rent records ledger" />
        {canManageLedger ? (
          <div className="flex flex-wrap items-end gap-2">
            <select
              className={`max-w-xs ${inputClass}`}
              value={rentPropertyId}
              onChange={(e) => setRentPropertyId(e.target.value)}
              aria-label="Property"
            >
              {dash.properties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <input
              className={`max-w-[140px] ${inputClass}`}
              value={rentAmount}
              onChange={(e) => setRentAmount(e.target.value)}
              aria-label="Rent amount"
            />
            <button type="button" className={btnPrimary} onClick={() => void onCreateRent()}>
              Add rent record
            </button>
          </div>
        ) : (
          <p className="text-sm text-slate-600">
            Read-only oversight. Rent ledger writes require the landlord role (`rent_records.manage`).
          </p>
        )}
        {rents.length === 0 ? (
          <EmptyState title="No rent records" description="No rent records yet." />
        ) : (
          <DataTable caption="Rent records">
            <thead>
              <tr>
                <Th>Property</Th>
                <Th>Amount</Th>
                <Th>Period</Th>
                <Th>Status</Th>
                {canManageLedger ? <Th>Actions</Th> : null}
              </tr>
            </thead>
            <tbody>
              {rents.map((row) => (
                <tr key={String(row.id)} className="hover:bg-slate-50">
                  <Td className="font-semibold text-slate-900">
                    {String(row.property_name)}
                    {row.tenancy_reference ? (
                      <span className="mt-0.5 block text-xs font-normal text-slate-500">{String(row.tenancy_reference)}</span>
                    ) : null}
                  </Td>
                  <Td>£{String(row.amount)}</Td>
                  <Td className="whitespace-nowrap">
                    {String(row.period_start)} → {String(row.period_end)}
                  </Td>
                  <Td>
                    <StatusChip status={String(row.status)} />
                  </Td>
                  {canManageLedger ? (
                    <Td>
                      <div className="flex flex-wrap gap-2">
                        {row.status !== "recorded_paid" ? (
                          <button type="button" className={btnSecondary} onClick={() => void onMarkPaid(String(row.id))}>
                            Record as paid
                          </button>
                        ) : null}
                        <button type="button" className={btnSecondary} onClick={() => void onArchiveRent(String(row.id))}>
                          Archive
                        </button>
                      </div>
                    </Td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </section>

      <section id="inspections" className="space-y-4">
        <CardHeader title="Inspections" />
        {canManageLedger ? (
          <div className="flex flex-wrap items-end gap-2">
            <select
              className={`max-w-xs ${inputClass}`}
              value={inspectionPropertyId}
              onChange={(e) => setInspectionPropertyId(e.target.value)}
              aria-label="Inspection property"
            >
              {dash.properties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <input
              className={`min-w-[180px] flex-1 ${inputClass}`}
              value={inspectionTitle}
              onChange={(e) => setInspectionTitle(e.target.value)}
              aria-label="Inspection title"
            />
            <input
              type="date"
              className={inputClass}
              value={inspectionDate}
              onChange={(e) => setInspectionDate(e.target.value)}
              aria-label="Scheduled date"
            />
            <button type="button" className={btnPrimary} onClick={() => void onCreateInspection()}>
              Schedule inspection
            </button>
          </div>
        ) : (
          <p className="text-sm text-slate-600">
            Read-only oversight. Inspection writes require the landlord role (`inspections.manage`).
          </p>
        )}
        <p className="text-sm text-slate-600">
          Upcoming: {dash.inspections.upcoming} · Overdue: {dash.inspections.overdue} · Completed: {dash.inspections.completed}
        </p>
        {inspections.length === 0 ? (
          <EmptyState title="No inspections" description="No inspections yet." />
        ) : (
          <DataTable caption="Inspections">
            <thead>
              <tr>
                <Th>Inspection</Th>
                <Th>Property</Th>
                <Th>Scheduled</Th>
                <Th>Status</Th>
                {canManageLedger ? <Th>Actions</Th> : null}
              </tr>
            </thead>
            <tbody>
              {inspections.map((row) => (
                <tr key={String(row.id)} className="hover:bg-slate-50">
                  <Td className="font-semibold text-slate-900">
                    {String(row.title)}
                    {row.findings ? <span className="mt-0.5 block text-xs font-normal text-slate-500">Findings: {String(row.findings)}</span> : null}
                    {row.follow_up_actions ? (
                      <span className="block text-xs font-normal text-slate-500">Follow-up: {String(row.follow_up_actions)}</span>
                    ) : null}
                  </Td>
                  <Td>{String(row.property_name)}</Td>
                  <Td className="whitespace-nowrap">{String(row.scheduled_date)}</Td>
                  <Td>
                    <StatusChip status={String(row.effective_status)} />
                  </Td>
                  {canManageLedger ? (
                    <Td>
                      {String(row.effective_status ?? row.status) !== "completed" ? (
                        <button type="button" className={btnSecondary} onClick={() => void onCompleteInspection(row)}>
                          Mark completed
                        </button>
                      ) : (
                        "—"
                      )}
                    </Td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </section>

      <section id="repairs" className="space-y-4">
        <CardHeader title="Repair oversight" />
        <p className="text-sm text-slate-600">
          Open: {dash.repairs.open} · Completed: {dash.repairs.completed} · Pending maintenance: {dash.repairs.pending_maintenance}
        </p>
        {repairs.length === 0 ? (
          <EmptyState title="No repairs" description="No repairs on your properties." />
        ) : (
          <DataTable caption="Repairs">
            <thead>
              <tr>
                <Th>Repair</Th>
                <Th>Property</Th>
                <Th>Priority</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {repairs.map((row) => (
                <tr key={String(row.id)} className="hover:bg-slate-50">
                  <Td className="font-semibold text-slate-900">
                    {String(row.title)}
                    {row.scheduled_visit_at ? (
                      <span className="mt-0.5 block text-xs font-normal text-slate-500">Scheduled {String(row.scheduled_visit_at)}</span>
                    ) : null}
                    {row.completion_notes ? (
                      <span className="block text-xs font-normal text-slate-500">Completion: {String(row.completion_notes)}</span>
                    ) : null}
                  </Td>
                  <Td>{String(row.property_name)}</Td>
                  <Td>
                    <StatusChip status={String(row.priority)} />
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-1.5">
                      <StatusChip status={String(row.status)} />
                      {row.is_overdue ? <StatusChip tone="red">Overdue</StatusChip> : null}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </section>
    </div>
  );
}
