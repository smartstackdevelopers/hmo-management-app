import Link from "next/link";
import { redirect } from "next/navigation";
import { readSessionAccessToken } from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { RecordPager } from "@/components/housing/RecordPager";
import {
  Avatar,
  DataTable,
  FilterTabs,
  StatusChip,
  Td,
  Th,
  btnPrimary,
  btnSecondary,
  inputClass,
  linkClass,
} from "@/components/ui/primitives";
import { fetchPortfolio } from "@/lib/landlordEnterpriseApi";
import { LOGIN_PATH, canAny } from "@/lib/rbac";
import { fetchRecordsPage, type PageResult } from "@/lib/recordsApi";
import { requireAuthenticatedSession } from "@/lib/session";

type PropertyRecord = {
  id: string;
  name: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  postcode: string;
  status: string;
};

type PortfolioFacts = {
  total_rooms?: unknown;
  occupied_rooms?: unknown;
  vacant_rooms?: unknown;
  maintenance_status?: unknown;
};

function propertiesHref(args: { q?: string; status?: string; focus?: string; page?: number }) {
  const search = new URLSearchParams();
  if (args.q) search.set("q", args.q);
  if (args.status) search.set("status", args.status);
  if (args.focus) search.set("focus", args.focus);
  if (args.page && args.page > 1) search.set("page", String(args.page));
  const query = search.toString();
  return query ? `/properties?${query}` : "/properties";
}

function countLabel(value: unknown): string | null {
  const n = Number(value);
  return Number.isFinite(n) ? String(n) : null;
}

function occupancyLabel(facts: PortfolioFacts | undefined): string | null {
  if (!facts) return null;
  const total = countLabel(facts.total_rooms);
  const occupied = countLabel(facts.occupied_rooms);
  if (total === null || occupied === null) return null;
  return `${occupied} / ${total}`;
}

export default async function PropertiesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; status?: string; focus?: string; page?: string }>;
}) {
  const params = await searchParams;
  const session = await requireAuthenticatedSession("/properties");
  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Sign-in isn't set up"
        description="Properties will show here once sign-in is configured."
      />
    );
  }
  if (!session.authorization) {
    return (
      <ErrorState
        title="We couldn't load your access"
        description="Your role and permissions didn't load. Please try again."
        retryHref="/properties"
      />
    );
  }
  if (!canAny(session.authorization.permissions, ["properties.read", "properties.manage"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return (
      <EmptyState
        title="Choose an organisation"
        description="Select an organisation to see its properties."
      />
    );
  }
  const token = await readSessionAccessToken();
  if (!token) {
    return (
      <EmptyState
        title="Please sign in again"
        description="Your session has ended. Sign in again to see properties."
        action={{ label: "Sign in", href: `${LOGIN_PATH}?returnTo=/properties` }}
      />
    );
  }

  const status = params.status === "active" || params.status === "archived" ? params.status : undefined;
  const q = params.q?.trim() || undefined;
  const sheetFocus = params.focus === "compliance" || params.focus === "licence" ? params.focus : undefined;
  const requestedFocus = params.focus === "vacancies" ? "vacancies" : undefined;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const canAdd = canAny(session.authorization.permissions, ["properties.manage"]);

  try {
    let portfolio: Map<string, PortfolioFacts> | null = null;
    try {
      const loaded = await fetchPortfolio({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization.active_role,
      });
      portfolio = new Map(
        (loaded.items ?? []).map((item) => [String(item.property_id), item as PortfolioFacts]),
      );
    } catch {
      portfolio = null;
    }
    const focus = portfolio && requestedFocus === "vacancies" ? "vacancies" : undefined;
    const filtered = Boolean(q || status || focus || sheetFocus);
    const sheetNote =
      sheetFocus === "compliance"
        ? "Certificate dates are not stored on properties yet."
        : sheetFocus === "licence"
          ? "HMO licence dates are not stored on properties yet."
          : null;

    const auth = {
      accessToken: token,
      organisationId: orgId,
      role: session.authorization.active_role ?? undefined,
    };
    let result: PageResult<PropertyRecord>;
    if (sheetNote) {
      result = { items: [], page: 1, page_size: 20, total: 0 };
    } else if (focus) {
      const pageSize = 100;
      const first = await fetchRecordsPage<PropertyRecord>("/api/v1/properties", {
        ...auth,
        query: { q, status, page: "1", page_size: String(pageSize) },
      });
      const loaded = [...first.items];
      const serverPages = Math.ceil(first.total / Math.max(first.page_size, 1));
      for (let p = 2; p <= serverPages && p <= 10; p += 1) {
        const next = await fetchRecordsPage<PropertyRecord>("/api/v1/properties", {
          ...auth,
          query: { q, status, page: String(p), page_size: String(pageSize) },
        });
        loaded.push(...next.items);
      }
      const matched = loaded.filter((row) => Number(portfolio?.get(row.id)?.vacant_rooms) > 0);
      const viewSize = 20;
      const start = (page - 1) * viewSize;
      result = {
        items: matched.slice(start, start + viewSize),
        page,
        page_size: viewSize,
        total: matched.length,
      };
    } else {
      result = await fetchRecordsPage<PropertyRecord>("/api/v1/properties", {
        ...auth,
        query: { q, status, page: String(page), page_size: "20" },
      });
    }

    const from = result.total === 0 ? 0 : (page - 1) * result.page_size + 1;
    const to = Math.min(page * result.page_size, result.total);
    const pageCount = Math.max(1, Math.ceil(result.total / Math.max(result.page_size, 1)));

    return (
      <div className="mx-auto max-w-6xl space-y-5">
        <PageHeader
          eyebrow="Portfolio / Properties"
          title="Properties"
          description="Every property and its rooms in one list."
          actions={
            <>
              {canAdd ? (
                <Link className={btnPrimary} href="/properties/new">
                  + Add property
                </Link>
              ) : null}
              <Link className={btnSecondary} href="/dashboard/documents/new">
                Import
              </Link>
            </>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="relative min-w-[16rem] flex-1">
            {status ? <input type="hidden" name="status" value={status} /> : null}
            {focus ? <input type="hidden" name="focus" value={focus} /> : null}
            <label className="sr-only" htmlFor="property-search">
              Search address or postcode
            </label>
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" strokeLinecap="round" />
              </svg>
            </span>
            <input
              id="property-search"
              name="q"
              defaultValue={q ?? ""}
              placeholder="Search address or postcode"
              className={`${inputClass} pl-9`}
            />
            <button type="submit" className="sr-only">
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: propertiesHref({ q }), active: !status && !focus && !sheetFocus },
              {
                label: "Vacancies",
                href: propertiesHref({ q, focus: "vacancies" }),
                active: focus === "vacancies",
              },
              {
                label: "Compliance due",
                href: propertiesHref({ q, focus: "compliance" }),
                active: sheetFocus === "compliance",
              },
              {
                label: "Licensed HMO",
                href: propertiesHref({ q, focus: "licence" }),
                active: sheetFocus === "licence",
              },
              { label: "Active", href: propertiesHref({ q, status: "active" }), active: status === "active" && !focus },
              {
                label: "Archived",
                href: propertiesHref({ q, status: "archived" }),
                active: status === "archived" && !focus,
              },
            ]}
          />
        </div>
        {result.items.length === 0 ? (
          <EmptyState
            title="No properties to show"
            description={
              sheetNote
                ? sheetNote
                : filtered
                  ? "No properties match this search."
                  : "There are no properties in this organisation yet."
            }
            action={
              filtered
                ? { label: "Clear filters", href: "/properties" }
                : canAdd
                  ? { label: "Add property", href: "/properties/new" }
                  : undefined
            }
          />
        ) : (
          <>
            <DataTable caption="Properties">
              <thead>
                <tr>
                  <Th>Property</Th>
                  <Th>Postcode</Th>
                  <Th>Rooms</Th>
                  <Th>Occupancy</Th>
                  <Th>Next certificate</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((row) => {
                  const facts = portfolio?.get(row.id);
                  const rooms = facts ? countLabel(facts.total_rooms) : null;
                  const occupancy = occupancyLabel(facts);
                  return (
                    <tr key={row.id} className="hover:bg-slate-50">
                      <Td>
                        <div className="flex items-center gap-3">
                          <Avatar name={row.name} size="sm" />
                          <Link href={`/properties/${row.id}`} className={`${linkClass} truncate`}>
                            {row.name}
                          </Link>
                        </div>
                      </Td>
                      <Td className="whitespace-nowrap">{row.postcode}</Td>
                      <Td>{rooms ?? "—"}</Td>
                      <Td className="whitespace-nowrap">{occupancy ?? "—"}</Td>
                      <Td className="whitespace-nowrap text-slate-400">—</Td>
                      <Td>
                        <StatusChip status={row.status} />
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </DataTable>
            <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-sm text-slate-500">
              <p>
                Showing {from}–{to} of {result.total}
              </p>
              <RecordPager page={page} pageCount={pageCount} hrefFor={(next) => propertiesHref({ q, status, focus, page: next })} />
            </div>
          </>
        )}
      </div>
    );
  } catch {
    return (
      <ErrorState
        description="We couldn't load properties. Please try again."
        retryHref="/properties"
      />
    );
  }
}
