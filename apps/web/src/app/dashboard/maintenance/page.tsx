import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { RecordPager } from "@/components/housing/RecordPager";
import { PriorityChip } from "@/components/maintenance/PriorityChip";
import { DataTable, FilterTabs, StatusChip, Td, Th, btnPrimary, btnSecondary, humanize, inputClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { isEmergencyRequest, listMaintenanceRequests, type MaintenanceRequest } from "@/lib/maintenanceApi";
import { canAny } from "@/lib/rbac";
import { fetchRecordsPage } from "@/lib/recordsApi";
import { requireAuthenticatedSession } from "@/lib/session";

function maintenanceHref(args: {
  q?: string;
  status?: string;
  priority?: string;
  pending?: string;
  view?: string;
  page?: number;
}) {
  const search = new URLSearchParams();
  if (args.q) search.set("q", args.q);
  if (args.status) search.set("status", args.status);
  if (args.priority) search.set("priority", args.priority);
  if (args.pending) search.set("pending", args.pending);
  if (args.view) search.set("view", args.view);
  if (args.page && args.page > 1) search.set("page", String(args.page));
  const query = search.toString();
  return query ? `/dashboard/maintenance?${query}` : "/dashboard/maintenance";
}

const REPORTED = new Set(["submitted", "acknowledged", "under_review", "reopened"]);
const APPROVED = new Set(["awaiting_approval", "approved", "assigned", "scheduled"]);
const IN_PROGRESS = new Set(["in_progress", "awaiting_parts", "on_hold"]);
const DONE = new Set(["completed", "closed"]);

function bookedLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return `Booked ${date.toLocaleDateString("en-GB", { day: "numeric", month: "short" })}`;
}

export default async function MaintenanceListPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; priority?: string; q?: string; pending?: string; view?: string; page?: string }>;
}) {
  const params = await searchParams;
  const session = await requireAuthenticatedSession("/dashboard/maintenance");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "maintenance.manage",
      "maintenance.read.own",
      "maintenance.read.assigned",
      "maintenance.create.own",
      "maintenance.create.assigned",
      "maintenance.read.property",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select an organisation to see its repairs." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in unavailable" description="We can't load repairs right now. Please try again later." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState title="Session expired" description="Please sign in again to see your repairs." />;
    const role = session.authorization?.active_role;
    const q = params.q?.trim() || undefined;
    const pageNumber = Math.max(1, Number(params.page ?? "1") || 1);
    const listView = params.view === "list";
    const pending = params.pending === "1" ? "1" : undefined;
    const page = await listMaintenanceRequests({
      accessToken: token,
      organisationId: orgId,
      role,
      status: params.status,
      priority: params.priority,
      pendingApproval: pending === "1",
      q,
      page: pageNumber,
    });
    const propertyNames = new Map<string, string>();
    const roomLabels = new Map<string, string>();
    if (canAny(session.authorization?.permissions, ["properties.read", "properties.manage"])) {
      try {
        const properties = await fetchRecordsPage<{ id: string; name: string }>("/api/v1/properties", {
          accessToken: token,
          organisationId: orgId,
          role: role ?? undefined,
          query: { page_size: "100" },
        });
        for (const row of properties.items) propertyNames.set(row.id, row.name);
      } catch {
        propertyNames.clear();
      }
    }
    if (canAny(session.authorization?.permissions, ["rooms.read", "rooms.manage"])) {
      try {
        const rooms = await fetchRecordsPage<{ id: string; label: string }>("/api/v1/rooms", {
          accessToken: token,
          organisationId: orgId,
          role: role ?? undefined,
          query: { page_size: "100" },
        });
        for (const row of rooms.items) roomLabels.set(row.id, row.label);
      } catch {
        roomLabels.clear();
      }
    }
    const canCreate = canAny(session.authorization?.permissions, [
      "maintenance.manage",
      "maintenance.create.own",
      "maintenance.create.assigned",
    ]);
    const filtered = Boolean(params.status || params.priority || q || pending === "1");
    const shared = { q, status: params.status, priority: params.priority, pending, view: listView ? "list" : undefined };
    const columns: { key: string; label: string; dot: string; items: MaintenanceRequest[] }[] = [
      { key: "reported", label: "Reported", dot: "bg-brand-600", items: [] },
      { key: "approved", label: "Approved", dot: "bg-amber-500", items: [] },
      { key: "progress", label: "In progress", dot: "bg-brand-600", items: [] },
      { key: "done", label: "Done", dot: "bg-emerald-500", items: [] },
    ];
    const other: MaintenanceRequest[] = [];
    for (const row of page.items) {
      if (REPORTED.has(row.status)) columns[0]?.items.push(row);
      else if (APPROVED.has(row.status)) columns[1]?.items.push(row);
      else if (IN_PROGRESS.has(row.status)) columns[2]?.items.push(row);
      else if (DONE.has(row.status)) columns[3]?.items.push(row);
      else other.push(row);
    }
    if (other.length > 0) {
      columns.push({ key: "other", label: "Other", dot: "bg-slate-400", items: other });
    }
    const from = page.total === 0 ? 0 : (page.page - 1) * page.page_size + 1;
    const to = Math.min(page.page * page.page_size, page.total);
    const pageCount = Math.max(1, Math.ceil(page.total / Math.max(page.page_size, 1)));
    const placeLine = (row: MaintenanceRequest) => {
      const property = propertyNames.get(row.property_id);
      const room = row.room_id ? roomLabels.get(row.room_id) : undefined;
      const place = [property, room].filter(Boolean).join(" · ");
      return place || row.reference_number;
    };
    return (
      <div className="mx-auto max-w-6xl space-y-5">
        <PageHeader
          eyebrow="Operations / Maintenance"
          title="Maintenance"
          description="All repairs across your portfolio."
          actions={
            <>
              {canCreate ? (
                <Link href="/dashboard/maintenance/new" className={btnPrimary}>
                  + New job
                </Link>
              ) : null}
              <Link href={maintenanceHref({ ...shared, view: listView ? undefined : "list", page: pageNumber })} className={btnSecondary}>
                {listView ? "Board" : "List view"}
              </Link>
            </>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="relative min-w-[16rem] flex-1">
            {params.status ? <input type="hidden" name="status" value={params.status} /> : null}
            {params.priority ? <input type="hidden" name="priority" value={params.priority} /> : null}
            {pending ? <input type="hidden" name="pending" value="1" /> : null}
            {listView ? <input type="hidden" name="view" value="list" /> : null}
            <label className="sr-only" htmlFor="repair-search">
              Search repairs
            </label>
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" strokeLinecap="round" />
              </svg>
            </span>
            <input id="repair-search" name="q" defaultValue={q ?? ""} placeholder="Search..." className={`${inputClass} pl-9`} />
            <button type="submit" className="sr-only">
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              {
                label: "All",
                href: maintenanceHref({ q, view: listView ? "list" : undefined }),
                active: !params.status && !params.priority && pending !== "1",
              },
              {
                label: "Urgent",
                href: maintenanceHref({ q, view: listView ? "list" : undefined, priority: "urgent" }),
                active: params.priority === "urgent" && pending !== "1",
              },
              {
                label: "Awaiting approval",
                href: maintenanceHref({ q, view: listView ? "list" : undefined, pending: "1" }),
                active: pending === "1",
              },
            ]}
          />
        </div>
        {page.items.length === 0 ? (
          <EmptyState
            title="No repairs found"
            description={filtered ? "No repairs match these filters." : "There are no repairs to show yet."}
            action={
              filtered
                ? { label: "Clear filters", href: "/dashboard/maintenance" }
                : canCreate
                  ? { label: "New job", href: "/dashboard/maintenance/new" }
                  : undefined
            }
          />
        ) : listView ? (
          <DataTable caption="Repairs">
            <thead>
              <tr>
                <Th>Repair</Th>
                <Th>Reference</Th>
                <Th>Reported</Th>
                <Th>Priority</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50">
                  <Td>
                    <Link href={`/dashboard/maintenance/${row.id}`} className="font-semibold text-slate-900 hover:text-brand-700 hover:underline">
                      {row.title}
                    </Link>
                    <p className="mt-0.5 text-xs text-slate-500">{placeLine(row)}</p>
                  </Td>
                  <Td className="text-slate-500">{row.reference_number}</Td>
                  <Td className="whitespace-nowrap">{new Date(row.reported_at).toLocaleDateString("en-GB")}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-1.5">
                      {isEmergencyRequest(row) ? <StatusChip tone="red">Emergency</StatusChip> : <PriorityChip priority={row.priority} />}
                    </div>
                  </Td>
                  <Td>
                    <StatusChip status={row.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        ) : (
          <div className={`grid items-start gap-4 ${columns.length > 4 ? "xl:grid-cols-5" : "lg:grid-cols-4"}`}>
            {columns.map((column) => (
              <section key={column.key} className="min-h-[28rem] rounded-2xl bg-slate-100/80 p-3">
                <h2 className="mb-3 flex items-center gap-2 px-1 text-sm font-semibold text-slate-800">
                  <span aria-hidden="true" className={`h-2 w-2 rounded-full ${column.dot}`} />
                  {column.label}
                  <span className="ml-auto text-slate-400">{column.items.length}</span>
                </h2>
                <div className="space-y-3">
                  {column.items.map((row) => {
                    const booked = bookedLabel(row.scheduled_visit_at);
                    return (
                      <Link
                        key={row.id}
                        href={`/dashboard/maintenance/${row.id}`}
                        className="block rounded-2xl border border-slate-200 bg-white p-4 shadow-card hover:border-brand-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                      >
                        <p className="font-semibold text-slate-900">{row.title}</p>
                        <p className="mt-0.5 text-xs text-slate-500">{placeLine(row)}</p>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {row.category_code ? <StatusChip tone="blue">{humanize(row.category_code)}</StatusChip> : null}
                          {isEmergencyRequest(row) ? <StatusChip tone="red">Emergency</StatusChip> : null}
                          {!isEmergencyRequest(row) && (row.priority === "urgent" || row.priority === "high") ? (
                            <StatusChip status={row.priority} />
                          ) : null}
                          {booked ? <StatusChip tone="indigo">{booked}</StatusChip> : null}
                          {DONE.has(row.status) ? <StatusChip status={row.status} /> : null}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        )}
        {page.total > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-sm text-slate-500">
            <p>
              Showing {from}–{to} of {page.total}
            </p>
            <RecordPager
              page={pageNumber}
              pageCount={pageCount}
              hrefFor={(next) => maintenanceHref({ ...shared, page: next })}
            />
          </div>
        ) : null}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "We couldn't load repairs."}
        retryHref="/dashboard/maintenance"
      />
    );
  }
}
