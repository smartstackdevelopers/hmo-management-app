"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, btnSecondary, DataTable, inputClass, labelClass, StatCard, StatGrid, StatusChip, Td, Th } from "@/components/ui/primitives";
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
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance"
        title="Finance and budgets"
        description={String(dash?.disclaimer ?? "Authorised ledger and budget records. No online payment processing.")}
      />

      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {pending && !dash ? <p className="text-sm text-slate-500">Loading…</p> : null}

      <StatGrid>
        <StatCard label="Income posted" value={String(dash?.income_posted ?? "—")} tone="green" />
        <StatCard label="Expense posted" value={String(dash?.expense_posted ?? "—")} />
        <StatCard label="Net posted" value={String(dash?.net_posted ?? "—")} />
        <StatCard label="Rent outstanding (ledger)" value={String(dash?.rent_outstanding_total ?? "—")} tone="amber" />
      </StatGrid>

      {canManage ? (
        <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <h2 className="text-base font-semibold text-slate-900">Add finance record</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass} htmlFor="finance-type">
                Type
              </label>
              <select id="finance-type" className={`mt-1.5 ${inputClass}`} value={recordType} onChange={(e) => setRecordType(e.target.value)}>
                <option value="income">income</option>
                <option value="expense">expense</option>
                <option value="other">other</option>
              </select>
            </div>
            <div>
              <label className={labelClass} htmlFor="finance-category">
                Category
              </label>
              <select id="finance-category" className={`mt-1.5 ${inputClass}`} value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="rent_income">rent_income</option>
                <option value="other_income">other_income</option>
                <option value="maintenance">maintenance</option>
                <option value="utilities">utilities</option>
                <option value="admin">admin</option>
                <option value="other_expense">other_expense</option>
              </select>
            </div>
            <div>
              <label className={labelClass} htmlFor="finance-amount">
                Amount
              </label>
              <input id="finance-amount" className={`mt-1.5 ${inputClass}`} value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            <div>
              <label className={labelClass} htmlFor="finance-date">
                Effective date
              </label>
              <input id="finance-date" type="date" className={`mt-1.5 ${inputClass}`} value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
            </div>
            <div className="md:col-span-2">
              <label className={labelClass} htmlFor="finance-description">
                Description
              </label>
              <input id="finance-description" className={`mt-1.5 ${inputClass}`} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
          </div>
          <button
            type="button"
            className={btnPrimary}
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
        <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <h2 className="text-base font-semibold text-slate-900">Budgets</h2>
          <button
            type="button"
            className={btnSecondary}
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
            <EmptyState title="No budgets yet" description="Create a budget when you are ready to plan the year." />
          ) : (
            <DataTable caption="Budgets">
              <thead>
                <tr>
                  <Th>Name</Th>
                  <Th>Status</Th>
                  <Th>Period</Th>
                </tr>
              </thead>
              <tbody>
                {budgets.map((b) => (
                  <tr key={String(b.id)}>
                    <Td className="font-semibold text-slate-900">{String(b.name)}</Td>
                    <Td>
                      <StatusChip status={String(b.status)} />
                    </Td>
                    <Td>
                      {String(b.period_start)} → {String(b.period_end)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </section>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <button type="button" className={btnSecondary} onClick={refresh}>
          Refresh
        </button>
        {canExport ? (
          <>
            {(["csv", "pdf", "xlsx"] as const).map((fmt) => (
              <button
                key={fmt}
                type="button"
                className={btnSecondary}
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

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-slate-900">Transaction history</h2>
        {!records.length ? (
          <EmptyState
            title="No finance records yet"
            description="Rent outstanding totals above come from the existing rent ledger."
          />
        ) : (
          <DataTable caption="Finance records">
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>Type</Th>
                <Th>Category</Th>
                <Th>Amount</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={String(r.id)} className="hover:bg-slate-50">
                  <Td className="whitespace-nowrap">{String(r.effective_date)}</Td>
                  <Td>{String(r.record_type)}</Td>
                  <Td>
                    {String(r.category_label)}
                    {r.rent_record_id ? <span className="block text-xs text-slate-500">Linked rent {String(r.rent_record_id)}</span> : null}
                  </Td>
                  <Td className="font-semibold text-slate-900">
                    {String(r.amount)} {String(r.currency)}
                  </Td>
                  <Td>
                    <StatusChip status={String(r.status)} />
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
