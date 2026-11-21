import type { ReactNode } from "react";
import { cookies } from "next/headers";
import { ActionTile, AttentionItem, Card, CardHeader, type Tone } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { DEMO_LOGIN_COOKIE, isWebDemoAuthEnabled } from "@/lib/demoAuth";
import { isNativeAuthEnabled, readNativeAccessToken } from "@/lib/nativeAuth";
import { DASHBOARD_NAV, filterNavItems } from "@/lib/navigation";
import type { PermissionId } from "@/lib/rbac";

const UK_TIME_ZONE = "Europe/London";

const MODULE_DESCRIPTIONS: Record<string, string> = {
  tenants: "Tenant records and contact details.",
  properties: "Buildings, addresses and compliance.",
  rooms: "Rooms, rents and availability.",
  "landlord-enterprise": "Occupancy, rent and repairs across your portfolio.",
  "room-occupancy": "Who lives where, and what is vacant.",
  "rent-payments": "Rent due, paid and overdue.",
  maintenance: "Report, track and close repairs.",
  complaints: "Log and resolve complaints.",
  "housing-applications": "New applications and decisions.",
  "waiting-list": "People waiting for a home.",
  "occupancy-survey": "Occupancy checks and surveys.",
  documents: "Certificates, policies and signed forms.",
  files: "Private files shared with you.",
  communications: "Messages, reminders and announcements.",
  "digital-id-esign": "ID checks and signatures.",
  "case-assignments": "Match support workers to tenants.",
  handovers: "Pass work between shifts and colleagues.",
  visits: "Planned and completed visits.",
  tasks: "Follow-ups and to-dos.",
  rota: "Shifts and cover.",
  workload: "Caseloads across the team.",
  training: "Training records and renewals.",
  lms: "Courses and learning.",
  "support-plans-dashboard": "Goals, reviews and progress.",
  safeguarding: "Safeguarding reminders and checks.",
  "safeguarding-alerts": "Early-warning alerts to review.",
  incidents: "Record and follow up incidents.",
  "case-summaries": "Draft case summaries for review.",
  "notes-analysis": "Themes and risks from support notes.",
  "employment-support": "Jobs, skills and CV help.",
  "benefits-navigator": "Check and apply for benefits.",
  "tenant-engagement": "Surveys, events and feedback.",
  "tenant-assistant": "Ask questions and get answers.",
  "wellbeing-resources": "Wellbeing guides and services.",
  "community-directory": "Local services and partners.",
  "help-near-me": "Reports from the Help Near Me map.",
  "contractor-marketplace": "Repair jobs open for contractors.",
  "org-workflows": "Approvals, forms and secure sharing.",
  automation: "Rules that save the team time.",
  finance: "Budgets and financial records.",
  reports: "Dashboards and exports.",
  "council-portal": "Share updates with council partners.",
  organisations: "Every organisation on HMore.",
  "platform-admin": "Platform settings and monitoring.",
  governance: "Compliance and data governance.",
  audit: "Who did what, and when.",
  privacy: "Data requests and consent.",
  backups: "Backup status and restores.",
  performance: "Speed and reliability checks.",
  integrations: "Connected services.",
  "ai-costs": "AI usage and spend.",
  "ai-feature-flags": "Turn AI features on or off.",
};

type HomeSession = {
  permissions?: PermissionId[];
  role?: string | null;
};

/** Returns the first name when it looks like a real person's name, otherwise null. */
export function firstName(name: string | null | undefined): string | null {
  const trimmed = name?.trim();
  if (!trimmed || trimmed.includes("@") || /^demo\b/i.test(trimmed) || /^hmore user$/i.test(trimmed)) {
    return null;
  }
  return trimmed.split(/\s+/)[0] ?? null;
}

export function greeting(name: string | null | undefined, now: Date = new Date()): string | null {
  const first = firstName(name);
  if (!first) return null;
  const hour = Number(
    new Intl.DateTimeFormat("en-GB", { hour: "numeric", hourCycle: "h23", timeZone: UK_TIME_ZONE }).format(now),
  );
  const part = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  return `${part}, ${first}`;
}

export function todayLabel(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: UK_TIME_ZONE,
  }).format(now);
}

export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

/**
 * Bearer token for the current server session.
 * Same order as getDashboardSession: demo cookie, then native cookie, then Auth0.
 */
export async function readSessionAccessToken(): Promise<string | null> {
  if (isWebDemoAuthEnabled()) {
    const jar = await cookies();
    const demo = jar.get(DEMO_LOGIN_COOKIE)?.value?.trim();
    if (demo) return demo;
  }
  if (isNativeAuthEnabled()) {
    return (await readNativeAccessToken()) ?? null;
  }
  if (isAuth0Configured() && auth0) {
    try {
      return (await auth0.getAccessToken())?.token ?? null;
    } catch {
      return null;
    }
  }
  return null;
}

/** Nav item ids the session can see (UI convenience only; the API still enforces access). */
export function visibleModuleIds(session: HomeSession): Set<string> {
  return new Set(
    filterNavItems(DASHBOARD_NAV, {
      authenticated: true,
      permissions: session.permissions,
      role: session.role,
    }).map((item) => item.id),
  );
}

function initialsFor(title: string): string {
  const words = title.split(/[\s&]+/).filter(Boolean);
  return ((words[0]?.[0] ?? "") + (words[1]?.[0] ?? words[0]?.[1] ?? "")).toUpperCase();
}

export type ExtraTile = { href: string; title: string; description?: string };

export function ModuleTiles({
  session,
  ids,
  extra = [],
  title = "Your tools",
  description,
  limit,
}: {
  session: HomeSession;
  ids: string[];
  extra?: ExtraTile[];
  title?: string;
  description?: string;
  limit?: number;
}) {
  const visible = filterNavItems(DASHBOARD_NAV, {
    authenticated: true,
    permissions: session.permissions,
    role: session.role,
  });
  const byId = new Map(visible.map((item) => [item.id, item]));
  const seen = new Set<string>();
  const tiles: ExtraTile[] = [];
  for (const id of ids) {
    const item = byId.get(id);
    if (item && !seen.has(item.href)) {
      seen.add(item.href);
      tiles.push({ href: item.href, title: item.label, description: MODULE_DESCRIPTIONS[item.id] });
    }
  }
  for (const tile of extra) {
    if (!seen.has(tile.href)) {
      seen.add(tile.href);
      tiles.push(tile);
    }
  }
  const shown = typeof limit === "number" ? tiles.slice(0, limit) : tiles;
  if (shown.length === 0) return null;

  return (
    <section aria-labelledby="home-modules-heading">
      <div className="mb-4">
        <h2 id="home-modules-heading" className="text-base font-semibold text-slate-900">
          {title}
        </h2>
        {description ? <p className="mt-0.5 text-sm text-slate-500">{description}</p> : null}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {shown.map((tile) => (
          <ActionTile
            key={tile.href}
            href={tile.href}
            title={tile.title}
            description={tile.description}
            initials={initialsFor(tile.title)}
          />
        ))}
      </div>
    </section>
  );
}

export type AttentionEntry = { key: string; title: string; meta?: string; tone?: Tone; href?: string };

export function AttentionCard({
  items,
  title = "Needs attention",
  emptyText = "Nothing needs your attention right now.",
}: {
  items: AttentionEntry[];
  title?: string;
  emptyText?: string;
}) {
  return (
    <Card>
      <CardHeader
        title={title}
        action={items.length > 0 ? <span className="text-xs text-slate-500">{plural(items.length, "item")}</span> : undefined}
      />
      {items.length > 0 ? (
        <ul className="-mx-2 divide-y divide-slate-100">
          {items.map((item) => (
            <AttentionItem key={item.key} title={item.title} meta={item.meta} tone={item.tone} href={item.href} />
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">{emptyText}</p>
      )}
    </Card>
  );
}

/** Main card + "Needs attention" side card; the side card fills the row when there is no main card. */
export function HomeColumns({ main, aside }: { main?: ReactNode; aside: ReactNode }) {
  if (!main) return <div>{aside}</div>;
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="min-w-0 lg:col-span-2">{main}</div>
      <div className="min-w-0">{aside}</div>
    </div>
  );
}
