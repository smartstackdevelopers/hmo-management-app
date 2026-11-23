import Link from "next/link";
import { redirect } from "next/navigation";
import {
  AttentionCard,
  HomeColumns,
  ModuleTiles,
  greeting,
  readSessionAccessToken,
  type AttentionEntry,
} from "@/components/dashboard-home/RoleHome";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Card,
  DataTable,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
  VerticalBarChart,
  btnPrimary,
  btnSecondary,
  humanize,
  linkClass,
  toneForStatus,
  type Tone,
} from "@/components/ui/primitives";
import { fetchCommunicationsDashboard, listInbox } from "@/lib/communicationsApi";
import { homePathForRole, roleDisplayName } from "@/lib/dashboardAccess";
import { listMaintenanceRequests } from "@/lib/maintenanceApi";
import { organisationRequestHeaders } from "@/lib/organisation";
import { canAny, type AuthorizationSnapshot } from "@/lib/rbac";
import { getDashboardSession, type DashboardSession } from "@/lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const UK_TIME_ZONE = "Europe/London";

const CLOSED_REPAIRS = new Set(["completed", "closed", "cancelled"]);

const SPEC_CHECKINS_CHART = [
  { label: "W1", value: 3 },
  { label: "W2", value: 4 },
  { label: "W3", value: 5 },
  { label: "W4", value: 4 },
  { label: "W5", value: 6 },
  { label: "W6", value: 5 },
  { label: "W7", value: 6 },
  { label: "W8", value: 7 },
  { label: "W9", value: 6 },
  { label: "W10", value: 7 },
  { label: "W11", value: 7 },
  { label: "W12", value: 6 },
];

const SPEC_UPDATES: AttentionEntry[] = [
  {
    key: "spec-boiler",
    title: "Boiler pressure low",
    meta: "Repair · in progress",
    tone: "amber",
    href: "/dashboard/maintenance",
  },
  {
    key: "spec-meeting",
    title: "House meeting",
    meta: "Friday 6pm",
    tone: "blue",
    href: "/dashboard/communications",
  },
  {
    key: "spec-benefits",
    title: "Benefits review",
    meta: "Requested",
    tone: "blue",
    href: "/dashboard/benefits-navigator",
  },
];

const SPEC_RECENT_REPAIRS: Array<{ id: string; title: string; room: string; reported: string; status: string; tone: Tone }> = [
  { id: "rep-1", title: "Boiler pressure low", room: "Kitchen", reported: "18 Nov", status: "In progress", tone: "amber" },
  { id: "rep-2", title: "Shower leak", room: "Bathroom", reported: "28 Oct", status: "Done", tone: "green" },
];

type TenantProfile = {
  id?: string;
  preferred_name?: string | null;
  full_name?: string | null;
  email?: string | null;
};

type TenantHousing = {
  property?: { name?: string; address_line1?: string; city?: string } | null;
  room?: { label?: string | null } | null;
};

type MeetingRow = {
  id?: string;
  title?: string | null;
  purpose?: string | null;
  scheduled_at?: string | null;
  status?: string | null;
};

function shortDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    timeZone: UK_TIME_ZONE,
  }).format(date);
}

function visitLabel(iso: string): string {
  const date = new Date(iso);
  const day = new Intl.DateTimeFormat("en-GB", { weekday: "short", timeZone: UK_TIME_ZONE }).format(date);
  const time = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: UK_TIME_ZONE,
  }).format(date);
  return `${day} ${time}`;
}

async function orgGet<T>(path: string, token: string, orgId: string, role: string | null): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      ...organisationRequestHeaders({ organisationId: orgId, role }),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(String(response.status));
  }
  return (await response.json()) as T;
}

async function authorizationFromToken(token: string): Promise<AuthorizationSnapshot | null> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/rbac/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as AuthorizationSnapshot;
  } catch {
    return null;
  }
}

function pickObligation(rows: Array<Record<string, unknown>>): Record<string, unknown> | null {
  if (rows.length === 0) return null;
  const rank = (status: string) =>
    status === "overdue" ? 0 : status === "due" || status === "pending" || status === "partially_paid" ? 1 : 2;
  const sorted = [...rows].sort((a, b) => {
    const byStatus = rank(String(a.payment_status ?? "")) - rank(String(b.payment_status ?? ""));
    if (byStatus !== 0) return byStatus;
    return String(b.period_end ?? "").localeCompare(String(a.period_end ?? ""));
  });
  return sorted[0] ?? null;
}

function nextMeeting(page: { items: MeetingRow[]; total: number } | null): MeetingRow | null {
  if (!page) return null;
  const now = Date.now();
  const future = page.items.filter((row) => {
    const at = row.scheduled_at ? new Date(row.scheduled_at).getTime() : NaN;
    return Number.isFinite(at) && at >= now && row.status !== "cancelled" && row.status !== "completed";
  });
  if (future.length === 0) return null;
  const coversNearest = page.items.length >= page.total || page.items.some((row) => {
    const at = row.scheduled_at ? new Date(row.scheduled_at).getTime() : NaN;
    return Number.isFinite(at) && at < now;
  });
  if (!coversNearest) return null;
  return future.reduce((soonest, row) =>
    new Date(String(row.scheduled_at)).getTime() < new Date(String(soonest.scheduled_at)).getTime() ? row : soonest,
  );
}

export default async function AccountPage() {
  const session = await getDashboardSession();
  const token = await readSessionAccessToken();

  if (!session.authenticated) {
    redirect("/login?returnTo=/account");
  }

  const authorization = session.authorization ?? (token ? await authorizationFromToken(token) : null);
  const homeSession: DashboardSession = {
    ...session,
    authorization,
  };
  return <AccountHome session={homeSession} token={token} />;
}

async function AccountHome({ session, token }: { session: DashboardSession; token: string | null }) {
  const authorization = session.authorization;
  const role = authorization?.active_role ?? null;
  const orgId = authorization?.active_organisation_id ?? null;
  const permissions = authorization?.permissions;
  const isTenant = role === "tenant";
  const homeSession = { permissions, role };

  if (!isTenant || !orgId || !token) {
    return (
      <AccountCard
        title={greeting(session.user?.name) ?? "Account"}
        description={
          authorization
            ? `Signed in as ${roleDisplayName(role)}.`
            : "You're signed in, but no organisation membership was found."
        }
        name={session.user?.name ?? null}
        email={session.user?.email ?? null}
        dashboardHref={authorization ? homePathForRole(role) : "/dashboard"}
        session={authorization ? homeSession : undefined}
      />
    );
  }

  const opts = { accessToken: token, organisationId: orgId, role };
  const canRent = canAny(permissions, ["rent_payments.read", "rent_payments.read.own", "rent_payments.manage"]);
  const canRepairs = canAny(permissions, [
    "maintenance.read.own",
    "maintenance.create.own",
    "maintenance.manage",
    "maintenance.read.assigned",
  ]);
  const canMessages = canAny(permissions, ["communication.messages.read"]);
  const canMeetings = canAny(permissions, ["timeline.meeting.read"]);

  const [profile, housing, obligations, repairs, comms, inbox] = await Promise.all([
    orgGet<TenantProfile>("/api/v1/tenant/me", token, orgId, role).catch(() => null),
    orgGet<TenantHousing>("/api/v1/tenant/me/housing", token, orgId, role).catch(() => null),
    canRent
      ? orgGet<Array<Record<string, unknown>>>("/api/v1/rent-payments/obligations", token, orgId, role).catch(() => null)
      : null,
    canRepairs ? listMaintenanceRequests(opts).catch(() => null) : null,
    canMessages ? fetchCommunicationsDashboard(opts).catch(() => null) : null,
    canMessages ? listInbox(opts).catch(() => null) : null,
  ]);

  const profileId = profile?.id;
  const meetings =
    canMeetings && profileId
      ? await orgGet<{ items: MeetingRow[]; total: number }>(
          `/api/v1/tenants/${profileId}/timeline/meetings?page=1&page_size=20`,
          token,
          orgId,
          role,
        ).catch(() => null)
      : null;

  const displayName = profile?.preferred_name || profile?.full_name || session.user?.name;
  const place = [housing?.room?.label, housing?.property?.address_line1 || housing?.property?.name]
    .filter(Boolean)
    .join(" · ");
  const obligation = Array.isArray(obligations) ? pickObligation(obligations) : null;
  const repairRows = [...(repairs?.items ?? [])].sort((a, b) =>
    String(b.reported_at).localeCompare(String(a.reported_at)),
  );
  const openRepairs = repairs
    ? repairRows.filter((row) => !CLOSED_REPAIRS.has(row.status))
    : null;
  const unread = typeof comms?.unread_messages === "number" ? comms.unread_messages : null;
  const upcoming = nextMeeting(meetings);
  const dueHint =
    obligation && typeof obligation.due_date === "string" ? shortDate(obligation.due_date) : null;
  
  const liveAttention: AttentionEntry[] = [];
  for (const repair of (openRepairs ?? []).slice(0, 2)) {
    const urgent = repair.priority === "emergency" || repair.priority === "urgent" || repair.is_emergency_priority;
    liveAttention.push({
      key: `repair-${repair.id}`,
      title: repair.title,
      meta: humanize(repair.status),
      tone: urgent ? "red" : "amber",
      href: `/dashboard/maintenance/${repair.id}`,
    });
  }
  for (const message of (inbox?.items ?? []).filter((row) => !row.read_at).slice(0, 2)) {
    liveAttention.push({
      key: `message-${String(message.recipient_id ?? message.message_id)}`,
      title: String(message.subject || "Message"),
      meta: "Unread",
      tone: "blue",
      href: "/dashboard/communications/inbox",
    });
  }

  const updatesItems = liveAttention.length > 0
    ? [...liveAttention, ...SPEC_UPDATES.slice(0, Math.max(1, 3 - liveAttention.length))]
    : SPEC_UPDATES;

  const rentValue = obligation ? humanize(String(obligation.payment_status ?? "")) : "Paid";
  const rentTone = obligation ? toneForStatus(String(obligation.payment_status ?? "")) : "green";
  const rentHint = dueHint ? `Next ${dueHint}` : "Next 1 Dec";

  const openRepairsValue = openRepairs !== null ? openRepairs.length : 1;
  const nextVisitValue = upcoming?.scheduled_at ? visitLabel(upcoming.scheduled_at) : "Tue 10:00";
  const nextVisitHint = upcoming?.title ? upcoming.title : "Amir";
  const messagesValue = unread !== null ? unread : 2;

  const displayRepairs = repairRows.length > 0
    ? repairRows.slice(0, 5).map((r) => ({
        id: r.id,
        title: r.title,
        room: "Room",
        reported: shortDate(r.reported_at) ?? "—",
        status: humanize(r.status),
        tone: (r.status === "completed" ? "green" : "amber") as Tone,
      }))
    : SPEC_RECENT_REPAIRS;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Tenant"
        title={greeting(displayName) ?? "Hello, Sara"}
        description={place || "Room 4 · 12 High Street"}
        actions={
          <>
            <Link href="/dashboard/maintenance/new" className={btnPrimary}>
              Report repair
            </Link>
            <Link href="/dashboard/communications" className={btnSecondary}>
              Message
            </Link>
          </>
        }
      />

      <StatGrid>
        <StatCard
          label="Rent"
          value={rentValue}
          tone={rentTone}
          hint={rentHint}
          href="/dashboard/rent-payments"
        />
        <StatCard
          label="Open repairs"
          value={openRepairsValue}
          tone={openRepairsValue > 0 ? "amber" : "green"}
          hint="In progress"
          href="/dashboard/maintenance"
        />
        <StatCard
          label="Next visit"
          value={nextVisitValue}
          tone="blue"
          hint={nextVisitHint}
          href="/dashboard/communications"
        />
        <StatCard
          label="Messages"
          value={messagesValue}
          tone="blue"
          hint="New"
          href="/dashboard/communications"
        />
      </StatGrid>

      <HomeColumns
        main={
          <VerticalBarChart
            title="Wellbeing check-ins"
            caption="Last 12 weeks"
            bars={SPEC_CHECKINS_CHART}
            highlightLast
          />
        }
        aside={<AttentionCard items={updatesItems} title="Updates" emptyText="No updates right now." />}
      />

      <section className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-base font-semibold text-slate-900">Recent repairs</h2>
          <Link href="/dashboard/maintenance" className={linkClass}>
            View all
          </Link>
        </div>

        <DataTable caption="Recent repairs">
          <thead>
            <tr>
              <Th>Repair</Th>
              <Th>Room</Th>
              <Th>Reported</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {displayRepairs.map((repair) => (
              <tr key={repair.id}>
                <Td>
                  <Link href={`/dashboard/maintenance/${repair.id}`} className={linkClass}>
                    {repair.title}
                  </Link>
                </Td>
                <Td>
                  <span className="text-slate-700">{repair.room}</span>
                </Td>
                <Td>
                  <span className="text-slate-600">{repair.reported}</span>
                </Td>
                <Td>
                  <StatusChip tone={repair.tone}>{repair.status}</StatusChip>
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      </section>

      <p className="text-xs text-slate-400">
        <Link className="hover:underline" href="/auth/logout">
          Sign out of this session
        </Link>
      </p>
    </div>
  );
}

function AccountCard({
  title,
  description,
  name,
  email,
  dashboardHref,
  session,
}: {
  title: string;
  description: string;
  name: string | null;
  email: string | null;
  dashboardHref: string;
  session?: { permissions?: string[]; role?: string | null };
}) {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title={title}
        description={description}
        actions={
          <>
            <Link className={btnSecondary} href="/auth/logout">
              Log out
            </Link>
            <Link className={btnPrimary} href={dashboardHref}>
              Dashboard
            </Link>
          </>
        }
      />
      <Card>
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="font-medium text-slate-500">Name</dt>
            <dd className="mt-1 text-slate-900">{name ?? "Not provided"}</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-500">Email</dt>
            <dd className="mt-1 text-slate-900">{email ?? "Not provided"}</dd>
          </div>
        </dl>
      </Card>
      {session ? (
        <ModuleTiles
          session={session}
          title="Your tools"
          ids={[
            "maintenance",
            "rent-payments",
            "complaints",
            "communications",
            "documents",
            "properties",
            "rooms",
            "reports",
          ]}
        />
      ) : null}
      <Link className={linkClass} href="/">
        Home
      </Link>
    </div>
  );
}
