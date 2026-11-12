"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  createFinanceBudget,
  createFinanceRecord,
  downloadFinanceExport,
  fetchFinanceBudgets,
  fetchFinanceDashboard,
  fetchFinanceRecords,
} from "@/lib/financeApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
  canBudget: boolean;
  canExport: boolean;
};

export function FinanceDashboard({
  accessToken,
  organisationId,
  role,
  canManage,
  canBudget,
  canExport,
}: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [records, setRecords] = useState<Record<string, unknown>[]>([]);
  const [budgets, setBudgets] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const [amount, setAmount] = useState("100.00");
  const [recordType, setRecordType] = useState("income");
  const [category, setCategory] = useState("other_income");
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        const [d, r] = await Promise.all([fetchFinanceDashboard(auth), fetchFinanceRecords(auth)]);
        setDash(d);
        setRecords(r.items);
        if (canBudget) {
          const b = await fetchFinanceBudgets(auth);
          setBudgets(b.items);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load finance");
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Finance &amp; budgets</h1>
        <p className="mt-1 text-sm text-slate-600">
          {String(dash?.disclaimer ?? "Authorised ledger and budget records. No online payment processing.")}
        </p>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {pending && !dash ? <p className="text-sm text-slate-500">Loading…</p> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {(
          [
            ["Income posted", dash?.income_posted],
            ["Expense posted", dash?.expense_posted],
            ["Net posted", dash?.net_posted],
            ["Rent outstanding (ledger)", dash?.rent_outstanding_total],
          ] as Array<[string, unknown]>
        ).map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
            <div className="mt-1 text-2xl font-semibold text-slate-900">{String(value ?? "—")}</div>
          </div>
        ))}
      </div>

      {canManage ? (
        <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-medium text-slate-800">Add finance record</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-sm">
              Type
              <select className="mt-1 w-full rounded border px-2 py-1.5" value={recordType} onChange={(e) => setRecordType(e.target.value)}>
                <option value="income">income</option>
                <option value="expense">expense</option>
                <option value="other">other</option>
              </select>
            </label>
            <label className="text-sm">
              Category
              <select className="mt-1 w-full rounded border px-2 py-1.5" value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="rent_income">rent_income</option>
                <option value="other_income">other_income</option>
                <option value="maintenance">maintenance</option>
                <option value="utilities">utilities</option>
                <option value="admin">admin</option>
                <option value="other_expense">other_expense</option>
              </select>
            </label>
            <label className="text-sm">
              Amount
              <input className="mt-1 w-full rounded border px-2 py-1.5" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </label>
            <label className="text-sm">
              Effective date
              <input type="date" className="mt-1 w-full rounded border px-2 py-1.5" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
            </label>
            <label className="text-sm md:col-span-2">
              Description
              <input className="mt-1 w-full rounded border px-2 py-1.5" value={description} onChange={(e) => setDescription(e.target.value)} />
            </label>
          </div>
          <button
            type="button"
            className="rounded bg-teal-800 px-3 py-2 text-sm font-medium text-white"
            onClick={() =>
              startTransition(async () => {
                try {
                  await createFinanceRecord(auth, {
                    record_type: recordType,
                    category_code: category,
                    amount,
                    effective_date: effectiveDate,
                    description,
                    status: "posted",
                  });
                  refresh();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Create failed");
                }
              })
            }
          >
            Create posted record
          </button>
        </section>
      ) : null}

      {canBudget ? (
        <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-medium text-slate-800">Budgets</h2>
          <button
            type="button"
            className="rounded border px-3 py-1.5 text-sm"
            onClick={() =>
              startTransition(async () => {
                const start = `${new Date().getFullYear()}-01-01`;
                const end = `${new Date().getFullYear()}-12-31`;
                try {
                  await createFinanceBudget(auth, {
                    name: `FY ${new Date().getFullYear()}`,
                    period_start: start,
                    period_end: end,
                    status: "active",
                    lines: [
                      { category_code: "maintenance", planned_amount: "5000.00" },
                      { category_code: "utilities", planned_amount: "2000.00" },
                    ],
                  });
                  refresh();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Budget create failed");
                }
              })
            }
          >
            Create sample annual budget
          </button>
          {!budgets.length ? (
            <p className="text-sm text-slate-500">No budgets yet.</p>
          ) : (
            <ul className="space-y-2">
              {budgets.map((b) => (
                <li key={String(b.id)} className="rounded border p-3 text-sm">
                  {String(b.name)} · {String(b.status)} · {String(b.period_start)} → {String(b.period_end)}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <button type="button" className="rounded border px-3 py-1.5 text-sm" onClick={refresh}>
          Refresh
        </button>
        {canExport ? (
          <>
            {(["csv", "pdf", "xlsx"] as const).map((fmt) => (
              <button
                key={fmt}
                type="button"
                className="rounded border px-3 py-1.5 text-sm"
                onClick={() =>
                  startTransition(async () => {
                    try {
                      await downloadFinanceExport(auth, fmt);
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Export failed");
                    }
                  })
                }
              >
                Export {fmt.toUpperCase()}
              </button>
            ))}
          </>
        ) : null}
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-slate-800">Transaction history</h2>
        {!records.length ? (
          <p className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">
            No finance records yet. Rent outstanding totals above come from the existing F6.1 rent ledger.
          </p>
        ) : (
          <ul className="space-y-2">
            {records.map((r) => (
              <li key={String(r.id)} className="rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm">
                {String(r.effective_date)} · {String(r.record_type)} · {String(r.category_label)} ·{" "}
                {String(r.amount)} {String(r.currency)} · {String(r.status)}
                {r.rent_record_id ? ` · linked rent ${String(r.rent_record_id)}` : ""}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
