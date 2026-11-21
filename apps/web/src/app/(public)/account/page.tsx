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
  btnPrimary,
  btnSecondary,
  humanize,
  linkClass,
  toneForStatus,
} from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchCommunicationsDashboard, listAnnouncements, listInbox } from "@/lib/communicationsApi";
import { homePathForRole, roleDisplayName } from "@/lib/dashboardAccess";
import { listMaintenanceRequests, type MaintenanceRequest } from "@/lib/maintenanceApi";
import { organisationRequestHeaders } from "@/lib/organisation";
import { canAny, type AuthorizationSnapshot } from "@/lib/rbac";
import { getDashboardSession, type DashboardSession } from "@/lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const UK_TIME_ZONE = "Europe/London";

const CLOSED_REPAIRS = new Set(["completed", "closed", "cancelled"]);

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
  if (!isAuth0Configured() || !auth0) {
    const session = await getDashboardSession();
    if (!session.authenticated) {
      return (
        <div className="mx-auto max-w-3xl">
          <PageHeader
            title="Sign-in not configured"
            description="Sign-in isn't set up in this environment yet."
          />
        </div>
      );
    }
    return <AccountHome session={session} token={await readSessionAccessToken()} />;
  }

  const authSession = await auth0.getSession();
  if (!authSession) {
    redirect("/auth/login?returnTo=/account");
  }

  const session = await getDashboardSession();
  let token: string | null = null;
  try {
    token = (await auth0.getAccessToken())?.token ?? null;
  } catch {
    token = null;
  }

  const authorization = session.authorization ?? (token ? await authorizationFromToken(token) : null);
  const user = authSession.user;
  const homeSession: DashboardSession = {
    authConfigured: true,
    authenticated: true,
    user: session.user ?? {
      sub: user.sub,
      email: user.email ?? null,
      name: user.name ?? user.nickname ?? null,
    },
    authorization,
    authorizationError: authorization ? "none" : session.authorizationError,
    authorizationDetail: session.authorizationDetail,
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

  const [profile, housing, obligations, repairs, comms, inbox, announcements] = await Promise.all([
    orgGet<TenantProfile>("/api/v1/tenant/me", token, orgId, role).catch(() => null),
    orgGet<TenantHousing>("/api/v1/tenant/me/housing", token, orgId, role).catch(() => null),
    canRent
      ? orgGet<Array<Record<string, unknown>>>("/api/v1/rent-payments/obligations", token, orgId, role).catch(() => null)
      : null,
    canRepairs ? listMaintenanceRequests(opts).catch(() => null) : null,
    canMessages ? fetchCommunicationsDashboard(opts).catch(() => null) : null,
    canMessages ? listInbox(opts).catch(() => null) : null,
    canAny(permissions, ["communication.announcements.read"])
      ? listAnnouncements(opts).catch(() => null)
      : null,
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
  const notices = Array.isArray(announcements) ? announcements : [];
  const visible = homeSession;

  const attention: AttentionEntry[] = [];
  for (const repair of (openRepairs ?? []).slice(0, 3)) {
    const urgent = repair.priority === "emergency" || repair.priority === "urgent" || repair.is_emergency_priority;
    attention.push({
      key: `repair-${repair.id}`,
      title: repair.title,
      meta: humanize(repair.status),
      tone: urgent ? "red" : "amber",
      href: `/dashboard/maintenance/${repair.id}`,
    });
  }
  for (const message of (inbox?.items ?? []).filter((row) => !row.read_at).slice(0, 3)) {
    attention.push({
      key: `message-${String(message.recipient_id ?? message.message_id)}`,
      title: String(message.subject || "Message"),
      meta: "Unread",
      tone: "indigo",
      href: "/dashboard/communications/inbox",
    });
  }
  for (const notice of notices.slice(0, 2)) {
    const title = String(notice.title ?? notice.subject ?? "");
    if (!title) continue;
    attention.push({
      key: `notice-${String(notice.id ?? title)}`,
      title,
      meta: "Announcement",
      tone: "blue",
      href: "/dashboard/communications/announcements",
    });
  }
  if (upcoming?.title && upcoming.scheduled_at) {
    attention.push({
      key: `meeting-${String(upcoming.id ?? upcoming.scheduled_at)}`,
      title: upcoming.title,
      meta: visitLabel(upcoming.scheduled_at),
      tone: "blue",
    });
  }

  const canReportRepair = canRepairs;
  const canMessage = canMessages;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Tenant"
        title={greeting(displayName) ?? "Your home"}
        description={place || "Rent, repairs and messages for your home."}
        actions={
          <>
            {canReportRepair ? (
              <Link href="/dashboard/maintenance/new" className={btnPrimary}>
                Report repair
              </Link>
            ) : null}
            {canMessage ? (
              <Link href="/dashboard/communications" className={btnSecondary}>
                Message
              </Link>
            ) : null}
          </>
        }
      />

      {obligation || openRepairs || unread !== null || upcoming?.scheduled_at ? (
        <StatGrid>
          {obligation ? (
            <StatCard
              label="Rent"
              value={humanize(String(obligation.payment_status ?? ""))}
              tone={toneForStatus(String(obligation.payment_status ?? ""))}
              hint={dueHint ? `Next ${dueHint}` : undefined}
              href="/dashboard/rent-payments"
            />
          ) : null}
          {openRepairs ? (
            <StatCard
              label="Open repairs"
              value={openRepairs.length}
              tone={openRepairs.some((row) => row.priority === "emergency" || row.is_emergency_priority) ? "red" : openRepairs.length ? "amber" : "green"}
              hint={openRepairs.some((row) => row.status === "in_progress") ? "In progress" : undefined}
              href="/dashboard/maintenance"
            />
          ) : null}
          {upcoming?.scheduled_at ? (
            <StatCard
              label="Next visit"
              value={visitLabel(upcoming.scheduled_at)}
              tone="blue"
              hint={upcoming.title && upcoming.title.length <= 24 ? upcoming.title : undefined}
            />
          ) : null}
          {unread !== null ? (
            <StatCard
              label="Messages"
              value={unread}
              tone={unread > 0 ? "indigo" : "gray"}
              hint={unread > 0 ? "New" : undefined}
              href="/dashboard/communications/inbox"
            />
          ) : null}
        </StatGrid>
      ) : null}

      <HomeColumns
        main={
          repairs ? (
            <div>
              <div className="mb-4 flex items-start justify-between gap-4">
                <h2 className="text-base font-semibold text-slate-900">Recent repairs</h2>
                <Link href="/dashboard/maintenance" className={linkClass}>
                  View all
                </Link>
              </div>
              {repairRows.length === 0 ? (
                <Card>
                  <p className="text-sm text-slate-500">No repairs reported yet.</p>
                </Card>
              ) : (
                <DataTable caption="Recent repairs">
                  <thead>
                    <tr>
                      <Th>Repair</Th>
                      <Th>Reported</Th>
                      <Th>Status</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {repairRows.slice(0, 6).map((repair) => (
                      <RepairRow key={repair.id} repair={repair} />
                    ))}
                  </tbody>
                </DataTable>
              )}
              {repairRows.length > 0 ? (
                <p className="mt-3 text-xs text-slate-500">
                  Showing 1–{Math.min(6, repairRows.length)} of {repairRows.length}
                </p>
              ) : null}
            </div>
          ) : undefined
        }
        aside={<AttentionCard items={attention} title="Updates" emptyText="No updates right now." />}
      />

      <ModuleTiles
        session={visible}
        title="Your home"
        ids={[
          "maintenance",
          "rent-payments",
          "complaints",
          "communications",
          "documents",
          "files",
          "housing-applications",
          "benefits-navigator",
          "tenant-engagement",
          "lms",
          "digital-id-esign",
          "tenant-assistant",
        ]}
      />

      <p className="text-sm text-slate-500">
        <Link className={linkClass} href="/auth/logout">
          Log out
        </Link>
      </p>
    </div>
  );
}

function RepairRow({ repair }: { repair: MaintenanceRequest }) {
  return (
    <tr>
      <Td>
        <Link href={`/dashboard/maintenance/${repair.id}`} className={linkClass}>
          {repair.title}
        </Link>
      </Td>
      <Td>{shortDate(repair.reported_at) ?? "—"}</Td>
      <Td>
        <StatusChip status={repair.status} />
      </Td>
    </tr>
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
