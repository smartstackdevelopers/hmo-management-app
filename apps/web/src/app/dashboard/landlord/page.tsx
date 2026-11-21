import Link from "next/link";
import {
  AttentionCard,
  HomeColumns,
  ModuleTiles,
  plural,
  readSessionAccessToken,
  type AttentionEntry,
} from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Avatar,
  Card,
  CardHeader,
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
} from "@/components/ui/primitives";
import { fetchLandlordDashboard, fetchPortfolio, type LandlordDashboard } from "@/lib/landlordEnterpriseApi";
import { LOGIN_PATH, canAny, type ApprovedRole } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { redirect } from "next/navigation";
import { LandlordEnterpriseClient } from "./LandlordEnterpriseClient";

/** Align with F6.1 nav: landlords own the tools; org/super admins may oversee via properties.* */
const LANDLORD_ENTERPRISE_ROLES: ApprovedRole[] = [
  "landlord",
  "organisation_admin",
  "super_admin",
];

function gbp(value: number): string {
  const whole = Number.isInteger(value);
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function text(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export default async function LandlordDashboardPage() {
  // F6.1 enterprise surface (also landlord role home). Do not gate on landlord-only —
  // nav lists org_admin/super_admin and backend scopes landlords to owned properties.
  const session = await requireAuthenticatedSession("/dashboard/landlord");

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so your portfolio can't load."
      />
    );
  }

  if (!session.authorization) {
    return (
      <ErrorState
        title="We couldn't load your access"
        description="Your role and permissions didn't load. Please try again in a moment."
        retryHref="/dashboard/landlord"
      />
    );
  }

  const activeRole = session.authorization.active_role as ApprovedRole | null;
  if (!activeRole || !LANDLORD_ENTERPRISE_ROLES.includes(activeRole)) {
    redirect("/unauthorized");
  }

  if (
    !canAny(session.authorization.permissions, [
      "properties.manage",
      "properties.read",
      "rent_records.manage",
      "inspections.manage",
      "repairs.status.read",
      "maintenance.read.property",
    ])
  ) {
    redirect("/unauthorized");
  }

  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return (
      <EmptyState
        title="Choose an organisation"
        description="Your account isn't linked to an active organisation yet, so there's no portfolio to show."
      />
    );
  }

  const token = await readSessionAccessToken();
  if (!token) {
    return (
      <EmptyState
        title="Please sign in again"
        description="Your session has ended. Sign in again to see your portfolio."
        action={{ label: "Sign in", href: `${LOGIN_PATH}?returnTo=/dashboard/landlord` }}
      />
    );
  }

  const permissions = session.authorization.permissions;
  const isLandlord = activeRole === "landlord";
  const canAddProperty = canAny(permissions, ["properties.manage"]);
  const canViewProperties = canAny(permissions, ["properties.read", "properties.manage"]);
  const homeSession = { permissions, role: activeRole };
  const opts = { accessToken: token, organisationId: orgId, role: session.authorization.active_role };

  let dash: LandlordDashboard | null = null;
  let portfolio: Array<Record<string, unknown>> = [];
  try {
    dash = await fetchLandlordDashboard(opts);
  } catch {
    dash = null;
  }
  try {
    portfolio = (await fetchPortfolio(opts)).items ?? [];
  } catch {
    portfolio = [];
  }

  const occupancy =
    dash && dash.total_rooms > 0 ? Math.round((dash.occupied_rooms / dash.total_rooms) * 100) : null;

  const attention: AttentionEntry[] = [];
  if (dash?.inspections.overdue) {
    attention.push({
      key: "inspections-overdue",
      title: plural(dash.inspections.overdue, "inspection") + " overdue",
      meta: "Past the scheduled date",
      tone: "red",
      href: "/dashboard/landlord#inspections",
    });
  }
  if (dash?.repairs.open) {
    attention.push({
      key: "repairs-open",
      title: plural(dash.repairs.open, "open repair"),
      meta: dash.repairs.pending_maintenance
        ? plural(dash.repairs.pending_maintenance, "repair") + " still with maintenance"
        : "On properties in this portfolio",
      tone: dash.repairs.open > 0 ? "amber" : "gray",
      href: "/dashboard/landlord#repairs",
    });
  }
  if (dash && dash.vacant_rooms > 0) {
    attention.push({
      key: "vacant-rooms",
      title: plural(dash.vacant_rooms, "vacant room"),
      tone: "amber",
      href: "/dashboard/landlord#portfolio",
    });
  }
  if (dash && dash.rent.outstanding > 0) {
    attention.push({
      key: "rent-outstanding",
      title: "Rent outstanding",
      meta: gbp(dash.rent.outstanding),
      tone: "amber",
      href: "/dashboard/landlord#rent",
    });
  }

  const description = dash
    ? `${plural(dash.total_properties, "property")} · ${plural(dash.total_rooms, "room")}`
    : isLandlord
      ? "Occupancy, rent, inspections and repairs for the properties you own."
      : "Occupancy, rent, inspections and repairs across landlord portfolios in your organisation.";

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        eyebrow={isLandlord ? "Landlord" : "Portfolio oversight"}
        title="Portfolio overview"
        description={description}
        actions={
          <>
            {canAddProperty ? (
              <Link href="/properties/new" className={btnPrimary}>
                + Add property
              </Link>
            ) : null}
            {canAny(permissions, ["reports.dashboard.view", "reports.housing.view", "reports.read"]) ? (
              <Link href="/dashboard/reports" className={btnSecondary}>
                Export
              </Link>
            ) : null}
          </>
        }
      />

      {dash ? (
        <StatGrid>
          <StatCard
            label="Occupancy"
            value={occupancy === null ? "—" : `${occupancy}%`}
            tone={dash.vacant_rooms > 0 ? "amber" : "green"}
            hint={
              dash.vacant_rooms > 0
                ? `${dash.vacant_rooms} vacant`
                : dash.total_rooms > 0
                  ? "Full"
                  : undefined
            }
            href="/dashboard/landlord#portfolio"
          />
          <StatCard
            label="Rent collected"
            value={gbp(dash.rent.recorded_paid)}
            tone={dash.rent.outstanding > 0 ? "amber" : "green"}
            hint={dash.rent.outstanding > 0 ? `${gbp(dash.rent.outstanding)} outstanding` : "Up to date"}
            href="/dashboard/landlord#rent"
          />
          <StatCard
            label="Open repairs"
            value={dash.repairs.open}
            tone={dash.repairs.open > 0 ? "red" : "green"}
            hint={dash.repairs.open > 0 ? "Open" : undefined}
            href="/dashboard/landlord#repairs"
          />
          <StatCard
            label="Certificates due"
            value="—"
            hint="Not on file"
            href="/dashboard/documents/expiring"
          />
        </StatGrid>
      ) : null}

      <HomeColumns
        main={
          <Card className="h-full">
            <CardHeader
              title="Rent collected"
              action={<span className="text-xs font-medium text-slate-400">Last 12 months</span>}
            />
            <p className="py-16 text-center text-sm text-slate-500">Monthly rent is not recorded on this portfolio yet.</p>
          </Card>
        }
        aside={<AttentionCard items={attention} emptyText="Nothing needs your attention right now." />}
      />

      {portfolio.length > 0 ? (
            <div>
              <div className="mb-4 flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Properties</h2>
                  <p className="mt-0.5 text-sm text-slate-500">Rooms and occupancy from your portfolio.</p>
                </div>
                {canViewProperties ? (
                  <Link href="/properties" className={linkClass}>
                    View all
                  </Link>
                ) : null}
              </div>
              <DataTable caption="Properties">
                <thead>
                  <tr>
                    <Th>Property</Th>
                    <Th>Rooms</Th>
                    <Th>Occupancy</Th>
                    <Th>Rent/month</Th>
                    <Th>Compliance</Th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.slice(0, 6).map((row) => {
                    const name = text(row.property_name);
                    const status = text(row.maintenance_status);
                    return (
                      <tr key={text(row.property_id)}>
                        <Td>
                          <div className="flex items-center gap-3">
                            <Avatar name={name} size="sm" />
                            <span className="font-semibold text-slate-900">{name}</span>
                          </div>
                        </Td>
                        <Td>{text(row.total_rooms)}</Td>
                        <Td>
                          {text(row.occupied_rooms)} / {text(row.total_rooms)}
                        </Td>
                        <Td className="text-slate-400">—</Td>
                        <Td>
                          <StatusChip tone={status === "attention" ? "red" : status === "clear" ? "green" : "gray"}>
                            {status === "clear" ? "Valid" : status === "attention" ? "Action" : humanize(status)}
                          </StatusChip>
                        </Td>
                      </tr>
                    );
                  })}
                </tbody>
              </DataTable>
              <p className="px-1 pt-3 text-xs text-slate-400">
                Showing 1–{Math.min(6, portfolio.length)} of {portfolio.length}
              </p>
            </div>
          ) : dash && dash.properties.length > 0 ? (
            <Card>
              <CardHeader title="Properties" />
              <ul className="-mx-2 divide-y divide-slate-100">
                {dash.properties.slice(0, 6).map((property) => (
                  <li key={property.id} className="flex items-center gap-3 px-2 py-2.5">
                    <Avatar name={property.name} size="sm" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-slate-900">{property.name}</span>
                      <span className="block truncate text-xs text-slate-500">
                        {[property.city, property.postcode].filter(Boolean).join(" · ")}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

      <ModuleTiles
        session={homeSession}
        title="Manage your portfolio"
        ids={[
          "properties",
          "rooms",
          "room-occupancy",
          "rent-payments",
          "maintenance",
          "complaints",
          "occupancy-survey",
          "documents",
          "communications",
          "council-portal",
          "reports",
        ]}
      />

      <section className="space-y-4" aria-labelledby="portfolio-records-heading">
        <h2 id="portfolio-records-heading" className="text-base font-semibold text-slate-900">
          Portfolio records
        </h2>
        <LandlordEnterpriseClient
          accessToken={token}
          organisationId={orgId}
          role={session.authorization.active_role}
        />
      </section>
    </div>
  );
}
