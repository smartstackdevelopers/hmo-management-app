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
  humanize,
  inputClass,
  linkClass,
} from "@/components/ui/primitives";
import { LOGIN_PATH, canAny } from "@/lib/rbac";
import { fetchRecordsPage } from "@/lib/recordsApi";
import { requireAuthenticatedSession } from "@/lib/session";

type RoomRecord = {
  id: string;
  property_id: string;
  label: string;
  floor_label?: string | null;
  room_type?: string | null;
  max_occupancy?: number | null;
  status: string;
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function roomsHref(args: { q?: string; status?: string; propertyId?: string; page?: number }) {
  const search = new URLSearchParams();
  if (args.q) search.set("q", args.q);
  if (args.status) search.set("status", args.status);
  if (args.propertyId) search.set("property_id", args.propertyId);
  if (args.page && args.page > 1) search.set("page", String(args.page));
  const query = search.toString();
  return query ? `/rooms?${query}` : "/rooms";
}

export default async function RoomsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; status?: string; property_id?: string; page?: string }>;
}) {
  const params = await searchParams;
  const session = await requireAuthenticatedSession("/rooms");
  if (!session.authConfigured) {
    return <EmptyState title="Sign-in isn't set up" description="Rooms will show here once sign-in is configured." />;
  }
  if (!session.authorization) {
    return (
      <ErrorState
        title="We couldn't load your access"
        description="Your role and permissions didn't load. Please try again."
        retryHref="/rooms"
      />
    );
  }
  if (!canAny(session.authorization.permissions, ["rooms.read", "rooms.manage"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select an organisation to see its rooms." />;
  }
  const token = await readSessionAccessToken();
  if (!token) {
    return (
      <EmptyState
        title="Please sign in again"
        description="Your session has ended. Sign in again to see rooms."
        action={{ label: "Sign in", href: `${LOGIN_PATH}?returnTo=/rooms` }}
      />
    );
  }

  const status = params.status === "active" || params.status === "archived" ? params.status : undefined;
  const q = params.q?.trim() || undefined;
  const propertyId = params.property_id && UUID.test(params.property_id) ? params.property_id : undefined;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const canAdd = canAny(session.authorization.permissions, ["rooms.manage"]);
  const filtered = Boolean(q || status || propertyId);

  try {
    const result = await fetchRecordsPage<RoomRecord>("/api/v1/rooms", {
      accessToken: token,
      organisationId: orgId,
      role: session.authorization.active_role ?? undefined,
      query: { q, status, property_id: propertyId, page: String(page), page_size: "20" },
    });
    const from = result.total === 0 ? 0 : (result.page - 1) * result.page_size + 1;
    const to = Math.min(result.page * result.page_size, result.total);

    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Portfolio / Rooms"
          title="Rooms"
          description="Rooms recorded against properties in this organisation."
          actions={
            canAdd ? (
              <Link className={btnPrimary} href="/rooms/new">
                + New room
              </Link>
            ) : null
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="relative min-w-[16rem] flex-1">
            {status ? <input type="hidden" name="status" value={status} /> : null}
            {propertyId ? <input type="hidden" name="property_id" value={propertyId} /> : null}
            <label className="sr-only" htmlFor="room-search">
              Search rooms
            </label>
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" strokeLinecap="round" />
              </svg>
            </span>
            <input id="room-search" name="q" defaultValue={q ?? ""} placeholder="Search rooms" className={`${inputClass} pl-9`} />
            <button type="submit" className="sr-only">
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: roomsHref({ q, propertyId }), active: !status },
              { label: "Active", href: roomsHref({ q, propertyId, status: "active" }), active: status === "active" },
              {
                label: "Archived",
                href: roomsHref({ q, propertyId, status: "archived" }),
                active: status === "archived",
              },
            ]}
          />
        </div>
        {result.items.length === 0 ? (
          <EmptyState
            title="No rooms to show"
            description={filtered ? "No rooms match this search." : "There are no rooms in this organisation yet."}
            action={
              filtered
                ? { label: "Clear filters", href: "/rooms" }
                : canAdd
                  ? { label: "New room", href: "/rooms/new" }
                  : undefined
            }
          />
        ) : (
          <>
            <DataTable caption="Rooms">
              <thead>
                <tr>
                  <Th>Room</Th>
                  <Th>Property</Th>
                  <Th>Floor</Th>
                  <Th>Type</Th>
                  <Th>Max occupancy</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50">
                    <Td>
                      <div className="flex items-center gap-3">
                        <Avatar name={row.label} size="sm" />
                        <span className="font-semibold text-slate-900">{row.label}</span>
                      </div>
                    </Td>
                    <Td>
                      <Link href={`/properties/${row.property_id}`} className={linkClass}>
                        View property
                      </Link>
                    </Td>
                    <Td>{row.floor_label || "—"}</Td>
                    <Td>{row.room_type ? humanize(row.room_type) : "—"}</Td>
                    <Td>{row.max_occupancy ?? "—"}</Td>
                    <Td>
                      <StatusChip status={row.status} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
            <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-sm text-slate-500">
              <p>
                Showing {from}–{to} of {result.total}
              </p>
              <RecordPager
                page={page}
                pageCount={Math.max(1, Math.ceil(result.total / Math.max(result.page_size, 1)))}
                hrefFor={(next) => roomsHref({ q, status, propertyId, page: next })}
              />
            </div>
          </>
        )}
      </div>
    );
  } catch {
    return <ErrorState description="We couldn't load rooms. Please try again." retryHref="/rooms" />;
  }
}
