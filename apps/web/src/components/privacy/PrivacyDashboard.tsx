"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorState } from "@/components/dashboard/ErrorState";
import {
  bootstrapPrivacyCatalog,
  fetchDataSubjectRequests,
  fetchDpiaRegister,
  fetchPrivacyDashboard,
  fetchPrivacyInventory,
  fetchPrivacyRisks,
  type PrivacyAuth,
} from "@/lib/privacyApi";

type Props = PrivacyAuth & { canManage: boolean };

export function PrivacyDashboard({ accessToken, organisationId, role, canManage }: Props) {
  const auth = { accessToken, organisationId, role };
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [inventory, setInventory] = useState<Record<string, unknown>[]>([]);
  const [dpia, setDpia] = useState<Record<string, unknown>[]>([]);
  const [dsrs, setDsrs] = useState<Record<string, unknown>[]>([]);
  const [risks, setRisks] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [d, inv, reg, dsrList, riskList] = await Promise.all([
        fetchPrivacyDashboard(auth),
        fetchPrivacyInventory(auth),
        fetchDpiaRegister(auth),
        fetchDataSubjectRequests(auth),
        fetchPrivacyRisks(auth),
      ]);
      setDash(d);
      setInventory(inv);
      setDpia(reg);
      setDsrs(dsrList);
      setRisks(riskList);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load privacy dashboard");
    } finally {
      setLoading(false);
    }
  }, [accessToken, organisationId, role]);

  useEffect(() => {
    void load();
  }, [load]);

  const onBootstrap = async () => {
    if (!canManage) return;
    try {
      await bootstrapPrivacyCatalog(auth);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bootstrap failed");
    }
  };

  if (loading && !dash) return <p className="text-sm text-slate-600">Loading privacy records…</p>;
  if (error) return <ErrorState description={error} />;

  const gate = (dash?.room_occupancy_privacy_gate ?? {}) as Record<string, unknown>;
  const actions = (dash?.outstanding_compliance_actions ?? []) as string[];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Privacy &amp; DPIA management</h1>
        <p className="mt-2 text-sm text-amber-900 rounded-md border border-amber-200 bg-amber-50 p-3">
          {String(
            dash?.legal_approval_notice ??
              "Technical records only — not legal certification. Authorised organisational approval required for DPIA and retention.",
          )}
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {(
          [
            ["Inventory items", dash?.inventory_item_count],
            ["Open DSRs", dash?.open_data_subject_requests],
            ["Open privacy risks", dash?.open_privacy_risks],
            ["Occupancy live", dash?.occupancy_live_status],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-1 text-xl font-semibold text-slate-900">{String(value ?? "—")}</p>
          </div>
        ))}
      </section>

      {canManage && (dash?.inventory_item_count as number) === 0 ? (
        <button
          type="button"
          onClick={() => void onBootstrap()}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Bootstrap data inventory &amp; DPIA templates
        </button>
      ) : null}

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-medium text-slate-900">Room occupancy privacy gate</h2>
        <p className="mt-2 text-sm text-slate-600">
          DPIA status: <strong>{String(gate.dpia_status ?? "unknown")}</strong> — gate complete:{" "}
          <strong>{gate.gate_complete ? "yes" : "no"}</strong>
        </p>
        <p className="mt-1 text-xs text-slate-500">{String(gate.privacy_notice ?? "")}</p>
      </section>

      <section>
        <h2 className="text-sm font-medium text-slate-900">Outstanding actions</h2>
        <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
          {actions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-sm font-medium text-slate-900">DPIA register ({dpia.length})</h2>
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <caption className="sr-only">DPIA activity status</caption>
            <thead>
              <tr className="border-b text-slate-500">
                <th scope="col" className="py-2 pr-4">
                  Activity
                </th>
                <th scope="col" className="py-2 pr-4">
                  Status
                </th>
                <th scope="col" className="py-2">
                  Approver
                </th>
              </tr>
            </thead>
            <tbody>
              {dpia.map((row) => (
                <tr key={String(row.id)} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{String(row.title)}</td>
                  <td className="py-2 pr-4">{String(row.status)}</td>
                  <td className="py-2">{String(row.approved_by_name ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-medium text-slate-900">Data inventory (sample)</h2>
        <ul className="mt-2 space-y-1 text-sm text-slate-700">
          {inventory.slice(0, 8).map((item) => (
            <li key={String(item.id)}>
              <span className="font-medium">{String(item.title)}</span>
              {item.lawful_basis_confirmed ? " ✓ basis noted" : " — basis pending"}
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="text-sm font-medium text-slate-900">Data subject requests</h2>
          <p className="mt-1 text-sm text-slate-600">{dsrs.length} recorded</p>
        </div>
        <div>
          <h2 className="text-sm font-medium text-slate-900">Privacy risk register</h2>
          <p className="mt-1 text-sm text-slate-600">{risks.length} entries</p>
        </div>
      </section>
    </div>
  );
}
