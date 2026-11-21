import { redirect } from "next/navigation";
import { readSessionAccessToken } from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Avatar,
  DataTable,
  FilterTabs,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
  humanize,
  inputClass,
} from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { fetchRecordsPage } from "@/lib/recordsApi";
import { requireAuthenticatedSession } from "@/lib/session";
import { getRentPaymentsDashboard, listRentObligations } from "@/lib/rentPaymentsApi";

const READ = ["rent_payments.read", "rent_payments.manage", "rent_payments.read.own"];

type Obligation = Record<string, unknown>;

function rentHref(args: { q?: string; status?: string }) {
  const search = new URLSearchParams();
  if (args.q) search.set("q", args.q);
  if (args.status) search.set("status", args.status);
  const query = search.toString();
  return query ? `/dashboard/rent-payments?${query}` : "/dashboard/rent-payments";
}

function formatAmount(value: unknown, currency: string | null): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(String(value).replace(/,/g, ""));
  if (!Number.isFinite(n)) return String(value);
  if (currency && /^[A-Z]{3}$/.test(currency)) {
    return new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(n);
  }
  return n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function text(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

const PILL_STATUS: { label: string; value: string }[] = [
  { label: "Paid", value: "paid" },
  { label: "Due", value: "due" },
  { label: "Late", value: "overdue" },
];

export default async function RentPaymentsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; status?: string }>;
}) {
  const params = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/rent-payments");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Rent payments unavailable"
        description="Choose an organisation and sign in to see rent payments."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Please sign in again to see rent payments." />;
  let stats: Record<string, unknown> = {};
  let obligations: Obligation[] = [];
  try {
    stats = await getRentPaymentsDashboard(token, orgId);
    obligations = await listRentObligations(token, orgId);
  } catch {
    return (
      <ErrorState description="Rent payments are turned off until an administrator approves them for this organisation." />
    );
  }

  const role = session.authorization?.active_role ?? undefined;
  const permissions = session.authorization?.permissions;
  const propertyNames = new Map<string, string>();
  const tenantNames = new Map<string, string>();
  const sessionToken = (await readSessionAccessToken()) || token;
  if (canAny(permissions, ["properties.read", "properties.manage"])) {
    try {
      const page = await fetchRecordsPage<{ id: string; name: string }>("/api/v1/properties", {
        accessToken: sessionToken,
        organisationId: orgId,
        role,
        query: { page_size: "100" },
      });
      for (const row of page.items) propertyNames.set(row.id, row.name);
    } catch {
      propertyNames.clear();
    }
  }
  if (canAny(permissions, ["tenants.read", "tenants.manage"])) {
    try {
      const page = await fetchRecordsPage<{ id: string; preferred_name: string }>("/api/v1/tenants", {
        accessToken: sessionToken,
        organisationId: orgId,
        role,
        query: { page_size: "100" },
      });
      for (const row of page.items) tenantNames.set(row.id, row.preferred_name);
    } catch {
      tenantNames.clear();
    }
  }

  const q = params.q?.trim().toLowerCase() || "";
  const present = new Set(obligations.map((row) => text(row.payment_status)).filter(Boolean));
  const extraStatuses = [...present].filter((value) => !PILL_STATUS.some((pill) => pill.value === value)).sort();
  const allowed = new Set([...PILL_STATUS.map((pill) => pill.value), ...extraStatuses]);
  const status = params.status && allowed.has(params.status) ? params.status : undefined;
  const visible = obligations.filter((row) => {
    if (status && text(row.payment_status) !== status) return false;
    if (!q) return true;
    const tenant = tenantNames.get(text(row.tenant_id)) ?? "";
    const property = propertyNames.get(text(row.property_id)) ?? "";
    const haystack = [tenant, property, text(row.tenancy_reference), text(row.tenant_id), text(row.property_id)]
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  });

  const currency =
    obligations.map((row) => text(row.currency)).find((code) => /^[A-Z]{3}$/.test(code)) || null;
  const due = Number(stats.total_rent_due);
  const received = Number(stats.total_rent_received);
  const collectedHint =
    Number.isFinite(due) && due > 0 && Number.isFinite(received) ? `${Math.round((received / due) * 100)}%` : undefined;
  const outstandingRows = obligations.filter((row) => Number(row.outstanding_balance) > 0);
  const tenantIds = new Set(outstandingRows.map((row) => text(row.tenant_id)).filter(Boolean));
  const outstandingHint =
    outstandingRows.length === 0
      ? undefined
      : tenantIds.size > 0 && tenantIds.size === outstandingRows.length
        ? `${tenantIds.size} ${tenantIds.size === 1 ? "tenant" : "tenants"}`
        : `${outstandingRows.length} open`;
  const overdueCount = Number(stats.overdue_count);
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/London",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const nextDue = obligations
    .filter((row) => {
      const paymentStatus = text(row.payment_status);
      const dueDate = text(row.due_date);
      return paymentStatus !== "paid" && paymentStatus !== "cancelled" && dueDate >= today;
    })
    .map((row) => text(row.due_date))
    .sort()[0];

  const collectedOf =
    Number.isFinite(received) && Number.isFinite(due)
      ? `${formatAmount(received, currency)} of ${formatAmount(due, currency)} collected`
      : "Rent that has been recorded, and what is still outstanding.";
  const showProperty = propertyNames.size > 0;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <PageHeader eyebrow="Portfolio / Rent payments" title="Rent payments" description={collectedOf} />
      <StatGrid>
        <StatCard
          label="Collected"
          value={stats.total_rent_received === undefined ? "—" : formatAmount(stats.total_rent_received, currency)}
          tone="green"
          hint={collectedHint}
        />
        <StatCard
          label="Outstanding"
          value={stats.outstanding_rent === undefined ? "—" : formatAmount(stats.outstanding_rent, currency)}
          tone="amber"
          hint={outstandingHint}
        />
        <StatCard
          label="Late"
          value={stats.overdue_count === undefined ? "—" : String(stats.overdue_count)}
          tone={Number.isFinite(overdueCount) && overdueCount > 0 ? "red" : "gray"}
        />
        <StatCard label="Next due" value={nextDue ? formatDate(nextDue) : "—"} />
      </StatGrid>
      <div className="flex flex-wrap items-center gap-3">
        <form method="get" className="relative min-w-[16rem] flex-1">
          {status ? <input type="hidden" name="status" value={status} /> : null}
          <label className="sr-only" htmlFor="rent-search">
            Search tenant or room
          </label>
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" strokeLinecap="round" />
            </svg>
          </span>
          <input
            id="rent-search"
            name="q"
            defaultValue={params.q ?? ""}
            placeholder="Search tenant or room"
            className={`${inputClass} pl-9`}
          />
          <button type="submit" className="sr-only">
            Search
          </button>
        </form>
        <FilterTabs
          tabs={[
            { label: "All", href: rentHref({ q: params.q?.trim() || undefined }), active: !status },
            ...PILL_STATUS.map((pill) => ({
              label: pill.label,
              href: rentHref({ q: params.q?.trim() || undefined, status: pill.value }),
              active: status === pill.value,
            })),
            ...extraStatuses.map((value) => ({
              label: humanize(value),
              href: rentHref({ q: params.q?.trim() || undefined, status: value }),
              active: status === value,
            })),
          ]}
        />
      </div>
      {visible.length === 0 ? (
        <EmptyState
          title="No rent obligations"
          description={
            q || status
              ? "No rent obligations match this search."
              : "No rent obligations have been synced for this organisation."
          }
          action={q || status ? { label: "Clear filters", href: "/dashboard/rent-payments" } : undefined}
        />
      ) : (
        <>
          <DataTable caption="Rent obligations">
            <thead>
              <tr>
                <Th>Tenant</Th>
                {showProperty ? <Th>Property</Th> : null}
                <Th>Amount</Th>
                <Th>Due</Th>
                <Th>Paid</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => {
                const rowCurrency = text(row.currency) || currency;
                const tenantName = tenantNames.get(text(row.tenant_id)) || text(row.tenancy_reference);
                const propertyName = propertyNames.get(text(row.property_id));
                return (
                  <tr key={text(row.rent_record_id)} className="hover:bg-slate-50">
                    <Td>
                      <div className="flex items-center gap-3">
                        {tenantName ? <Avatar name={tenantName} size="sm" /> : null}
                        <span className="font-semibold text-slate-900">{tenantName || "—"}</span>
                      </div>
                    </Td>
                    {showProperty ? <Td>{propertyName || "—"}</Td> : null}
                    <Td className="font-semibold text-slate-900">{formatAmount(row.rent_amount, rowCurrency)}</Td>
                    <Td className="whitespace-nowrap">{formatDate(row.due_date)}</Td>
                    <Td>{formatAmount(row.amount_paid, rowCurrency)}</Td>
                    <Td>
                      <StatusChip status={text(row.payment_status) === "overdue" ? "late" : text(row.payment_status)}>
                        {text(row.payment_status) === "overdue" ? "Late" : undefined}
                      </StatusChip>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </DataTable>
          <p className="px-1 text-sm text-slate-500">
            Showing 1–{visible.length} of {obligations.length}
          </p>
        </>
      )}
    </div>
  );
}
