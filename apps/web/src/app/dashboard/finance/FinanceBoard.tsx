"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  DataTable,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
  btnPrimary,
  btnSecondary,
  humanize,
  inputClass,
  labelClass,
} from "@/components/ui/primitives";
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

type Category = { code: string; label: string };

function money(value: unknown): string {
  if (value == null || value === "") return "—";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(amount);
}

function categoriesOf(dash: Record<string, unknown> | null): Category[] {
  if (!Array.isArray(dash?.categories)) return [];
  return dash.categories.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const row = item as Record<string, unknown>;
    if (typeof row.code !== "string") return [];
    return [{ code: row.code, label: typeof row.label === "string" ? row.label : humanize(row.code) }];
  });
}

function friendly(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) return fallback;
  const text = error.message.trim();
  if (!text || text.startsWith("{") || text.startsWith("[") || text.length > 180) return fallback;
  return text;
}

export function FinanceBoard({ accessToken, organisationId, role, canManage, canBudget, canExport }: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [records, setRecords] = useState<Record<string, unknown>[]>([]);
  const [budgets, setBudgets] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [recordType, setRecordType] = useState("income");
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [budgetName, setBudgetName] = useState("");
  const [budgetStart, setBudgetStart] = useState(`${new Date().getFullYear()}-01-01`);
  const [budgetEnd, setBudgetEnd] = useState(`${new Date().getFullYear()}-12-31`);
  const [budgetCategory, setBudgetCategory] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");

  const categories = categoriesOf(dash);

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        const [dashboard, recordPage] = await Promise.all([fetchFinanceDashboard(auth), fetchFinanceRecords(auth)]);
        setDash(dashboard);
        setRecords(recordPage.items);
        const nextCategories = categoriesOf(dashboard);
        setCategory((current) => current || nextCategories[0]?.code || "");
        setBudgetCategory((current) => current || nextCategories[0]?.code || "");
        if (canBudget) {
          const budgetPage = await fetchFinanceBudgets(auth);
          setBudgets(budgetPage.items);
        }
      } catch (loadError) {
        setError(friendly(loadError, "Finance records could not be loaded."));
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const from = records.length === 0 ? 0 : 1;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Insights / Finance"
        title="Finance"
        description="Income, budgets and spend across the organisation."
        actions={
          <>
            {canExport ? (
              <button
                type="button"
                className={btnPrimary}
                disabled={pending}
                onClick={() =>
                  startTransition(async () => {
                    try {
                      await downloadFinanceExport(auth, "csv");
                    } catch (exportError) {
                      setError(friendly(exportError, "The export could not be downloaded."));
                    }
                  })
                }
              >
                Export
              </button>
            ) : null}
            {canBudget ? (
              <a href="#new-budget" className={btnSecondary}>
                + Budget
              </a>
            ) : null}
          </>
        }
      />

      {error ? <ErrorState description={error} /> : null}
      {pending && !dash ? <p className="text-sm text-slate-500">Loading finance records…</p> : null}

      <StatGrid>
        <StatCard label="Income posted" value={money(dash?.income_posted)} tone="green" />
        <StatCard label="Expense posted" value={money(dash?.expense_posted)} />
        <StatCard label="Outstanding rent" value={money(dash?.rent_outstanding_total)} tone="amber" />
        <StatCard label="Net posted" value={money(dash?.net_posted)} />
      </StatGrid>

      {typeof dash?.disclaimer === "string" ? (
        <p className="text-sm text-slate-500">{dash.disclaimer}</p>
      ) : null}

      {records.length === 0 && dash ? (
        <EmptyState
          title="No finance records yet"
          description="Posted income and expenses will be listed here. Outstanding rent above comes from the rent ledger."
        />
      ) : null}
      {records.length > 0 ? (
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
            {records.map((row) => (
              <tr key={String(row.id)} className="hover:bg-slate-50">
                <Td className="whitespace-nowrap">{String(row.effective_date ?? "—")}</Td>
                <Td>{humanize(String(row.record_type ?? ""))}</Td>
                <Td>{String(row.category_label || "—")}</Td>
                <Td className="font-semibold text-slate-900">
                  {money(row.amount)}
                </Td>
                <Td>
                  <StatusChip status={String(row.status ?? "")} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      ) : null}
      {dash ? (
        <p className="text-xs text-slate-500">
          Showing {from}–{records.length} of {records.length}
        </p>
      ) : null}

      {canManage ? (
        <form
          className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
          onSubmit={(event) => {
            event.preventDefault();
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
                setAmount("");
                setDescription("");
                refresh();
              } catch (createError) {
                setError(friendly(createError, "The record could not be saved."));
              }
            });
          }}
        >
          <h2 className="text-base font-semibold text-slate-900">Add finance record</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="finance-type">
                Type
              </label>
              <select id="finance-type" className={inputClass} value={recordType} onChange={(event) => setRecordType(event.target.value)}>
                <option value="income">Income</option>
                <option value="expense">Expense</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="finance-category">
                Category
              </label>
              <select id="finance-category" className={inputClass} value={category} onChange={(event) => setCategory(event.target.value)}>
                {categories.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="finance-amount">
                Amount
              </label>
              <input id="finance-amount" className={inputClass} value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" required />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="finance-date">
                Effective date
              </label>
              <input id="finance-date" type="date" className={inputClass} value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} required />
            </div>
            <div className="space-y-1.5 md:col-span-2">
              <label className={labelClass} htmlFor="finance-description">
                Description
              </label>
              <input id="finance-description" className={inputClass} value={description} onChange={(event) => setDescription(event.target.value)} />
            </div>
          </div>
          <button type="submit" className={btnPrimary} disabled={pending || !category}>
            Save record
          </button>
        </form>
      ) : null}

      {canBudget ? (
        <section id="new-budget" className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <h2 className="text-base font-semibold text-slate-900">Budgets</h2>
          {budgets.length === 0 ? (
            <EmptyState title="No budgets yet" description="Add a budget when you are ready to plan the year." />
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
                {budgets.map((budget) => (
                  <tr key={String(budget.id)}>
                    <Td className="font-semibold text-slate-900">{String(budget.name)}</Td>
                    <Td>
                      <StatusChip status={String(budget.status ?? "")} />
                    </Td>
                    <Td>
                      {String(budget.period_start)} – {String(budget.period_end)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
          <form
            className="grid gap-4 md:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              startTransition(async () => {
                try {
                  await createFinanceBudget(auth, {
                    name: budgetName.trim(),
                    period_start: budgetStart,
                    period_end: budgetEnd,
                    status: "active",
                    lines: [{ category_code: budgetCategory, planned_amount: budgetAmount }],
                  });
                  setBudgetName("");
                  setBudgetAmount("");
                  refresh();
                } catch (budgetError) {
                  setError(friendly(budgetError, "The budget could not be saved."));
                }
              });
            }}
          >
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="budget-name">
                Name
              </label>
              <input id="budget-name" className={inputClass} value={budgetName} onChange={(event) => setBudgetName(event.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="budget-category">
                Category
              </label>
              <select id="budget-category" className={inputClass} value={budgetCategory} onChange={(event) => setBudgetCategory(event.target.value)}>
                {categories.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="budget-start">
                Period start
              </label>
              <input id="budget-start" type="date" className={inputClass} value={budgetStart} onChange={(event) => setBudgetStart(event.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="budget-end">
                Period end
              </label>
              <input id="budget-end" type="date" className={inputClass} value={budgetEnd} onChange={(event) => setBudgetEnd(event.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass} htmlFor="budget-amount">
                Planned amount
              </label>
              <input id="budget-amount" className={inputClass} value={budgetAmount} onChange={(event) => setBudgetAmount(event.target.value)} inputMode="decimal" required />
            </div>
            <div className="flex items-end">
              <button type="submit" className={btnPrimary} disabled={pending || !budgetCategory}>
                Save budget
              </button>
            </div>
          </form>
        </section>
      ) : null}
    </div>
  );
}
