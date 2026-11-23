import Link from "next/link";
import { redirect } from "next/navigation";
import { readSessionAccessToken } from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import {
  Avatar,
  Card,
  CardHeader,
  DataTable,
  StatusChip,
  Td,
  Th,
  btnPrimary,
  humanize,
  linkClass,
} from "@/components/ui/primitives";
import { fetchInspections, fetchPortfolio, fetchRentRecords, fetchRepairs } from "@/lib/landlordEnterpriseApi";
import { organisationRequestHeaders } from "@/lib/organisation";
import { LOGIN_PATH, canAny } from "@/lib/rbac";
import { fetchRecordsPage } from "@/lib/recordsApi";
import { requireAuthenticatedSession } from "@/lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type PropertyRecord = {
  id: string;
  name: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  region?: string | null;
  postcode: string;
  country_code: string;
  status: string;
  notes?: string | null;
};

type RoomRecord = {
  id: string;
  label: string;
  floor_label?: string | null;
  room_type?: string | null;
  max_occupancy?: number | null;
  status: string;
};

type TenantRecord = {
  id: string;
  preferred_name: string;
  assigned_property_id?: string | null;
  assigned_room_id?: string | null;
  status: string;
};

type RepairRow = {
  id?: unknown;
  title?: unknown;
  status?: unknown;
  priority?: unknown;
  created_at?: unknown;
  scheduled_visit_at?: unknown;
};

type InspectionRow = {
  id?: unknown;
  title?: unknown;
  status?: unknown;
  effective_status?: unknown;
  scheduled_date?: unknown;
  completed_date?: unknown;
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const CLOSED_REPAIR = new Set(["completed", "closed", "cancelled"]);

function fact(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function asText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function formatDay(value: unknown): string | null {
  if (typeof value !== "string" || !value) return null;
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function money(value: unknown, currency: string | null): string | null {
  const n = typeof value === "number" ? value : Number(String(value ?? "").replace(/,/g, ""));
  if (!Number.isFinite(n)) return null;
  if (currency && /^[A-Z]{3}$/.test(currency)) {
    return new Intl.NumberFormat("en-GB", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  }
  return n.toLocaleString("en-GB", { maximumFractionDigits: 0 });
}

export default async function PropertyDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const session = await requireAuthenticatedSession(`/properties/${id}`);
  if (!session.authConfigured) {
    return (
      <EmptyState title="Sign-in isn't set up" description="This property will show here once sign-in is configured." />
    );
  }
  if (!session.authorization) {
    return (
      <ErrorState
        title="We couldn't load your access"
        description="Your role and permissions didn't load. Please try again."
        retryHref={`/properties/${id}`}
      />
    );
  }
  if (!canAny(session.authorization.permissions, ["properties.read", "properties.manage"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select an organisation to see this property." />;
  }
  const token = await readSessionAccessToken();
  if (!token) {
    return (
      <EmptyState
        title="Please sign in again"
        description="Your session has ended. Sign in again to see this property."
        action={{ label: "Sign in", href: `${LOGIN_PATH}?returnTo=${encodeURIComponent(`/properties/${id}`)}` }}
      />
    );
  }
  if (!UUID.test(id)) {
    return (
      <EmptyState
        title="Property not found"
        description="That link doesn't match a property in this organisation."
        action={{ label: "Back to properties", href: "/properties" }}
      />
    );
  }

  const role = session.authorization.active_role;
  const permissions = session.authorization.permissions;
  try {
    const response = await fetch(`${API_BASE}/api/v1/properties/${id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        ...organisationRequestHeaders({ organisationId: orgId, role }),
      },
      cache: "no-store",
    });
    if (response.status === 404) {
      return (
        <EmptyState
          title="Property not found"
          description="That property isn't in this organisation, or the link is out of date."
          action={{ label: "Back to properties", href: "/properties" }}
        />
      );
    }
    if (response.status === 403) {
      return (
        <ErrorState
          title="You can't view this property"
          description="Your account doesn't have access to this property."
          retryHref="/properties"
        />
      );
    }
    if (!response.ok) {
      return (
        <ErrorState description="We couldn't load this property. Please try again." retryHref={`/properties/${id}`} />
      );
    }
    const property = (await response.json()) as PropertyRecord;

    let rooms: RoomRecord[] | null = null;
    try {
      const roomPage = await fetchRecordsPage<RoomRecord>("/api/v1/rooms", {
        accessToken: token,
        organisationId: orgId,
        role: role ?? undefined,
        query: { property_id: id, page_size: "100" },
      });
      rooms = roomPage.items;
    } catch {
      rooms = null;
    }

    let occupancy: {
      total_rooms?: unknown;
      occupied_rooms?: unknown;
      vacant_rooms?: unknown;
      occupancy_rate?: unknown;
      outstanding_repairs?: unknown;
      last_inspection_date?: unknown;
      tenancy_status?: unknown;
    } | null = null;
    try {
      const portfolio = await fetchPortfolio({
        accessToken: token,
        organisationId: orgId,
        role,
        query: { property_id: id },
      });
      const match = (portfolio.items ?? []).find((item) => String(item.property_id) === id);
      occupancy = match ?? null;
    } catch {
      occupancy = null;
    }

    let tenants: TenantRecord[] | null = null;
    if (canAny(permissions, ["tenants.read", "tenants.manage"])) {
      try {
        const tenantPage = await fetchRecordsPage<TenantRecord>("/api/v1/tenants", {
          accessToken: token,
          organisationId: orgId,
          role: role ?? undefined,
          query: { page_size: "100", status: "active" },
        });
        tenants = tenantPage.items.filter((tenant) => tenant.assigned_property_id === id);
      } catch {
        tenants = null;
      }
    }

    let repairs: RepairRow[] | null = null;
    try {
      const loaded = await fetchRepairs({
        accessToken: token,
        organisationId: orgId,
        role,
        query: { property_id: id, page_size: "100" },
      });
      repairs = loaded.items as RepairRow[];
    } catch {
      repairs = null;
    }

    let inspections: InspectionRow[] | null = null;
    try {
      const loaded = await fetchInspections({
        accessToken: token,
        organisationId: orgId,
        role,
        query: { property_id: id, page_size: "100" },
      });
      inspections = loaded.items as InspectionRow[];
    } catch {
      inspections = null;
    }

    let monthlyRent: string | null = null;
    try {
      const rent = await fetchRentRecords({
        accessToken: token,
        organisationId: orgId,
        role,
        query: { property_id: id, page_size: "100" },
      });
      const today = new Intl.DateTimeFormat("en-CA", {
        timeZone: "Europe/London",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date());
      const current = (rent.items ?? []).filter((row) => {
        const start = asText(row.period_start);
        const end = asText(row.period_end);
        return start && end && start <= today && today <= end;
      });
      if (current.length > 0) {
        const currency = current.map((row) => asText(row.currency)).find((code) => /^[A-Z]{3}$/.test(code)) || null;
        const total = current.reduce((sum, row) => sum + Number(row.amount), 0);
        monthlyRent = Number.isFinite(total) ? money(total, currency) : null;
      }
    } catch {
      monthlyRent = null;
    }

    const canAddRoom = canAny(permissions, ["rooms.manage"]);
    const address = [property.address_line1, property.address_line2].filter(Boolean).join(", ");
    const totalRooms = occupancy ? Number(occupancy.total_rooms) : rooms ? rooms.length : Number.NaN;
    const occupiedRooms = occupancy ? Number(occupancy.occupied_rooms) : Number.NaN;
    const vacantRooms = occupancy ? Number(occupancy.vacant_rooms) : Number.NaN;
    const openRepairs = repairs
      ? repairs.filter((row) => !CLOSED_REPAIR.has(asText(row.status))).length
      : occupancy
        ? Number(occupancy.outstanding_repairs)
        : Number.NaN;

    const roomName = new Map((rooms ?? []).map((room) => [room.id, room.label]));
    const occupiedRoomIds = new Set((tenants ?? []).map((tenant) => tenant.assigned_room_id).filter(Boolean));
    const vacantRoomLabels =
      rooms && tenants
        ? rooms.filter((room) => room.status === "active" && !occupiedRoomIds.has(room.id)).map((room) => room.label)
        : [];

    const todayStamp = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Europe/London",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    const nextInspection = (inspections ?? [])
      .map((row) => asText(row.scheduled_date))
      .filter((value) => value >= todayStamp)
      .sort()[0];
    const lastInspection = occupancy ? formatDay(occupancy.last_inspection_date) : null;

    const activity = [
      ...(inspections ?? []).map((row) => ({
        id: asText(row.id) || asText(row.title),
        title: asText(row.title) || "Inspection",
        detail: humanize(asText(row.effective_status) || asText(row.status)),
        at: asText(row.completed_date) || asText(row.scheduled_date),
      })),
      ...(repairs ?? []).map((row) => ({
        id: asText(row.id) || asText(row.title),
        title: asText(row.title) || "Repair",
        detail: humanize(asText(row.status)),
        at: asText(row.created_at) || asText(row.scheduled_visit_at),
      })),
    ]
      .filter((event) => event.at)
      .sort((a, b) => (a.at < b.at ? 1 : -1));

    const tabs = [
      { id: "overview", label: "Overview" },
      { id: "rooms", label: "Rooms" },
      ...(tenants ? [{ id: "tenants", label: "Tenants" }] : []),
      ...(repairs ? [{ id: "repairs", label: "Repairs" }] : []),
      ...(inspections ? [{ id: "inspections", label: "Inspections" }] : []),
    ];
    const tab = tabs.some((item) => item.id === query.tab) ? query.tab! : "overview";
    const tabHref = (next: string) => (next === "overview" ? `/properties/${id}` : `/properties/${id}?tab=${next}`);

    const subtitle = [property.city, property.postcode, Number.isFinite(totalRooms) ? `${totalRooms} rooms` : null]
      .filter(Boolean)
      .join(" · ");

    return (
      <div className="mx-auto max-w-6xl space-y-5">
        <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">
              Portfolio / Properties / {property.name}
            </p>
            <div className="mt-2 flex items-center gap-3">
              <span
                aria-hidden="true"
                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-700"
              >
                <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z" strokeLinejoin="round" />
                </svg>
              </span>
              <div className="min-w-0">
                <h1 className="truncate text-2xl font-bold tracking-tight text-slate-900 md:text-3xl">{property.name}</h1>
                <p className="mt-0.5 text-sm text-slate-500">
                  {subtitle || [address, property.city, property.postcode].filter(Boolean).join(", ")}
                </p>
              </div>
            </div>
          </div>
          {canAddRoom ? (
            <Link href="/rooms/new" className={btnPrimary}>
              Add room
            </Link>
          ) : null}
        </header>
        <div className="flex flex-wrap gap-2">
          <StatusChip status={property.status} />
          {Number.isFinite(vacantRooms) && vacantRooms > 0 ? (
            <StatusChip tone="amber">{vacantRooms} vacant</StatusChip>
          ) : null}
        </div>

        <nav aria-label="Property sections" className="flex gap-5 border-b border-slate-200">
          {tabs.map((item) => (
            <Link
              key={item.id}
              href={tabHref(item.id)}
              aria-current={tab === item.id ? "page" : undefined}
              className={`-mb-px border-b-2 pb-2 text-sm font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 ${
                tab === item.id ? "border-brand-700 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            {tab === "overview" ? (
              <>
                <Card>
                  <CardHeader title="Overview" />
                  <dl className="grid gap-x-6 gap-y-5 text-sm sm:grid-cols-3">
                    {Number.isFinite(totalRooms) ? (
                      <div>
                        <dt className="text-slate-500">Rooms</dt>
                        <dd className="mt-1 text-lg font-bold text-slate-900">
                          {Number.isFinite(occupiedRooms) ? `${totalRooms} (${occupiedRooms} let)` : totalRooms}
                        </dd>
                      </div>
                    ) : null}
                    {monthlyRent ? (
                      <div>
                        <dt className="text-slate-500">Monthly rent</dt>
                        <dd className="mt-1 text-lg font-bold text-slate-900">{monthlyRent}</dd>
                      </div>
                    ) : null}
                    {Number.isFinite(openRepairs) ? (
                      <div>
                        <dt className="text-slate-500">Open repairs</dt>
                        <dd className="mt-1 text-lg font-bold text-slate-900">{openRepairs}</dd>
                      </div>
                    ) : null}
                    {nextInspection ? (
                      <div>
                        <dt className="text-slate-500">Next inspection</dt>
                        <dd className="mt-1 text-lg font-bold text-slate-900">{formatDay(nextInspection)}</dd>
                      </div>
                    ) : lastInspection ? (
                      <div>
                        <dt className="text-slate-500">Last inspection</dt>
                        <dd className="mt-1 text-lg font-bold text-slate-900">{lastInspection}</dd>
                      </div>
                    ) : null}
                    <div>
                      <dt className="text-slate-500">Address</dt>
                      <dd className="mt-1 font-semibold text-slate-900">{fact(address)}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Postcode</dt>
                      <dd className="mt-1 font-semibold text-slate-900">{fact(property.postcode)}</dd>
                    </div>
                  </dl>
                  {property.notes ? (
                    <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-700">{property.notes}</p>
                  ) : null}
                </Card>
                <Card>
                  <CardHeader title="Activity timeline" />
                  {activity.length === 0 ? (
                    <p className="text-sm text-slate-500">No inspections or repairs recorded for this property.</p>
                  ) : (
                    <ol className="space-y-4">
                      {activity.slice(0, 12).map((event, index) => (
                        <li key={`${event.id}-${index}`} className="flex gap-3">
                          <span className="flex flex-col items-center">
                            <span
                              aria-hidden="true"
                              className={`mt-1.5 h-2.5 w-2.5 rounded-full ${index === 0 ? "bg-brand-600" : "bg-slate-300"}`}
                            />
                            {index < Math.min(activity.length, 12) - 1 ? (
                              <span aria-hidden="true" className="mt-1 w-px flex-1 bg-slate-200" />
                            ) : null}
                          </span>
                          <div className="flex min-w-0 flex-1 items-start justify-between gap-3 pb-1">
                            <div>
                              <p className="text-sm font-semibold text-slate-900">{event.title}</p>
                              {event.detail && event.detail !== "—" ? (
                                <p className="text-sm text-slate-500">{event.detail}</p>
                              ) : null}
                            </div>
                            <p className="shrink-0 text-xs text-slate-500">{formatDay(event.at) ?? event.at}</p>
                          </div>
                        </li>
                      ))}
                    </ol>
                  )}
                </Card>
              </>
            ) : null}

            {tab === "rooms" ? (
              <Card>
                <CardHeader title="Rooms" description="Rooms recorded against this property." />
                {rooms === null ? (
                  <p className="text-sm text-slate-500">Rooms could not be loaded.</p>
                ) : rooms.length === 0 ? (
                  <p className="text-sm text-slate-500">No rooms for this property yet.</p>
                ) : (
                  <DataTable caption="Rooms">
                    <thead>
                      <tr>
                        <Th>Room</Th>
                        <Th>Floor</Th>
                        <Th>Type</Th>
                        <Th>Max occupancy</Th>
                        <Th>Status</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {rooms.map((room) => (
                        <tr key={room.id}>
                          <Td className="font-semibold text-slate-900">{room.label}</Td>
                          <Td>{fact(room.floor_label)}</Td>
                          <Td>{room.room_type ? humanize(room.room_type) : "—"}</Td>
                          <Td>{fact(room.max_occupancy)}</Td>
                          <Td>
                            <StatusChip status={room.status} />
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </DataTable>
                )}
              </Card>
            ) : null}

            {tab === "tenants" && tenants ? (
              <Card>
                <CardHeader title="Tenants" description="Active tenants assigned to this property." />
                {tenants.length === 0 ? (
                  <p className="text-sm text-slate-500">No active tenants are assigned to this property.</p>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {tenants.map((tenant) => (
                      <li key={tenant.id} className="flex items-center gap-3 py-3">
                        <Avatar name={tenant.preferred_name} size="sm" />
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-semibold text-slate-900">{tenant.preferred_name}</span>
                          <span className="block truncate text-xs text-slate-500">
                            {tenant.assigned_room_id ? roomName.get(tenant.assigned_room_id) || "Room assigned" : "No room assigned"}
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            ) : null}

            {tab === "repairs" && repairs ? (
              <Card>
                <CardHeader title="Repairs" />
                {repairs.length === 0 ? (
                  <p className="text-sm text-slate-500">No repairs recorded for this property.</p>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {repairs.map((row, index) => {
                      const repairId = asText(row.id);
                      const title = asText(row.title) || "Repair";
                      return (
                        <li key={repairId || index} className="flex items-center justify-between gap-3 py-3">
                          <span className="min-w-0">
                            {repairId ? (
                              <Link href={`/dashboard/maintenance/${repairId}`} className={linkClass}>
                                {title}
                              </Link>
                            ) : (
                              <span className="text-sm font-semibold text-slate-900">{title}</span>
                            )}
                          </span>
                          <StatusChip status={asText(row.status)} />
                        </li>
                      );
                    })}
                  </ul>
                )}
              </Card>
            ) : null}

            {tab === "inspections" && inspections ? (
              <Card>
                <CardHeader title="Inspections" />
                {inspections.length === 0 ? (
                  <p className="text-sm text-slate-500">No inspections recorded for this property.</p>
                ) : (
                  <DataTable caption="Inspections">
                    <thead>
                      <tr>
                        <Th>Inspection</Th>
                        <Th>Scheduled</Th>
                        <Th>Status</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {inspections.map((row, index) => (
                        <tr key={asText(row.id) || index}>
                          <Td className="font-semibold text-slate-900">{asText(row.title) || "—"}</Td>
                          <Td>{formatDay(row.scheduled_date) ?? "—"}</Td>
                          <Td>
                            <StatusChip status={asText(row.effective_status) || asText(row.status)} />
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </DataTable>
                )}
              </Card>
            ) : null}
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader title="Next actions" />
              {vacantRoomLabels.length === 0 && !(repairs && repairs.some((row) => !CLOSED_REPAIR.has(asText(row.status)))) ? (
                <p className="text-sm text-slate-500">Nothing open on this property.</p>
              ) : (
                <ul className="space-y-3 text-sm">
                  {vacantRoomLabels.map((label) => (
                    <li key={label} className="text-slate-800">
                      {label} has no assigned tenant
                    </li>
                  ))}
                  {(repairs ?? [])
                    .filter((row) => !CLOSED_REPAIR.has(asText(row.status)))
                    .map((row, index) => {
                      const repairId = asText(row.id);
                      const title = asText(row.title) || "Repair";
                      return (
                        <li key={repairId || index}>
                          {repairId ? (
                            <Link href={`/dashboard/maintenance/${repairId}`} className={linkClass}>
                              {title}
                            </Link>
                          ) : (
                            <span className="text-slate-800">{title}</span>
                          )}
                        </li>
                      );
                    })}
                </ul>
              )}
            </Card>
            {tenants && tenants.length > 0 ? (
              <Card>
                <CardHeader title="Tenants" />
                <ul className="space-y-3">
                  {tenants.slice(0, 8).map((tenant) => (
                    <li key={tenant.id} className="flex items-center gap-3">
                      <Avatar name={tenant.preferred_name} size="sm" />
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold text-slate-900">{tenant.preferred_name}</span>
                        <span className="block truncate text-xs text-slate-500">
                          {tenant.assigned_room_id
                            ? roomName.get(tenant.assigned_room_id) || "Room assigned"
                            : "No room assigned"}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            ) : null}
          </div>
        </div>
        <p className="text-sm">
          <Link href="/properties" className={linkClass}>
            Back to properties
          </Link>
        </p>
      </div>
    );
  } catch {
    return (
      <ErrorState description="We couldn't load this property. Please try again." retryHref={`/properties/${id}`} />
    );
  }
}
