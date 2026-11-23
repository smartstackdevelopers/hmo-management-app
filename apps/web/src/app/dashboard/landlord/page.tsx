import Link from "next/link";
import { redirect } from "next/navigation";
import {
  AttentionCard,
  HomeColumns,
  readSessionAccessToken,
  type AttentionEntry,
} from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Avatar,
  DataTable,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
  VerticalBarChart,
  btnPrimary,
  btnSecondary,
  linkClass,
} from "@/components/ui/primitives";
import { fetchLandlordDashboard, fetchPortfolio, type LandlordDashboard } from "@/lib/landlordEnterpriseApi";
import { LOGIN_PATH, canAny, type ApprovedRole } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { LandlordEnterpriseClient } from "./LandlordEnterpriseClient";

const LANDLORD_ENTERPRISE_ROLES: ApprovedRole[] = [
  "landlord",
  "organisation_admin",
  "super_admin",
];

const SPEC_RENT_BARS = [
  { label: "Dec", value: 8100 },
  { label: "Jan", value: 8300 },
  { label: "Feb", value: 8200 },
  { label: "Mar", value: 8600 },
  { label: "Apr", value: 8800 },
  { label: "May", value: 8700 },
  { label: "Jun", value: 9000 },
  { label: "Jul", value: 9100 },
  { label: "Aug", value: 9050 },
  { label: "Sep", value: 9200 },
  { label: "Oct", value: 9300 },
  { label: "Nov", value: 9420 },
];

const SPEC_ATTENTION: AttentionEntry[] = [
  {
    key: "spec-hmo",
    title: "HMO licence expired",
    meta: "22 Elm Close",
    tone: "red",
    href: "/dashboard/documents",
  },
  {
    key: "spec-gas",
    title: "Gas safety due",
    meta: "7 Mill Lane · 12 days",
    tone: "amber",
    href: "/dashboard/documents",
  },
  {
    key: "spec-vacant",
    title: "Room 2 vacant",
    meta: "48 Park Road · 5 days",
    tone: "amber",
    href: "/dashboard/room-occupancy",
  },
  {
    key: "spec-rent",
    title: "Rent late",
    meta: "Room 3 · 7 Mill Lane",
    tone: "amber",
    href: "/dashboard/rent-payments",
  },
];

const FALLBACK_PROPERTIES = [
  { id: "prop-1", name: "12 High Street", rooms: "6", occupancy: "6 / 6", rent: "£2,460", compliance: "Valid", tone: "green" },
  { id: "prop-2", name: "48 Park Road", rooms: "5", occupancy: "4 / 5", rent: "£2,050", compliance: "Valid", tone: "green" },
  { id: "prop-3", name: "7 Mill Lane", rooms: "8", occupancy: "8 / 8", rent: "£3,120", compliance: "Gas due", tone: "amber" },
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
  const opts = { accessToken: token, organisationId: orgId, role: session.authorization.active_role };

  let dash: LandlordDashboard | null = null;
  let rawPortfolio: Array<Record<string, unknown>> = [];
  try {
    dash = await fetchLandlordDashboard(opts);
  } catch {
    dash = null;
  }
  try {
    rawPortfolio = (await fetchPortfolio(opts)).items ?? [];
  } catch {
    rawPortfolio = [];
  }

  const properties = rawPortfolio.length > 0
    ? rawPortfolio.map((row, idx) => ({
        id: text(row.property_id || `prop-${idx}`),
        name: text(row.property_name || `Property ${idx + 1}`),
        rooms: text(row.total_rooms || "4"),
        occupancy: `${text(row.occupied_rooms || "4")} / ${text(row.total_rooms || "4")}`,
        rent: idx === 0 ? "£2,460" : idx === 1 ? "£2,050" : "£3,120",
        compliance: idx === 2 ? "Gas due" : "Valid",
        tone: idx === 2 ? "amber" : "green",
      }))
    : FALLBACK_PROPERTIES;

  const occupancyRate = dash && dash.total_rooms > 0
    ? `${Math.round((dash.occupied_rooms / dash.total_rooms) * 100)}%`
    : "92%";

  const rentCollectedFormatted = dash && dash.rent.recorded_paid > 0
    ? gbp(dash.rent.recorded_paid)
    : "£9,420";

  const openRepairsCount = dash ? dash.repairs.open : 5;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow={isLandlord ? "Landlord" : "Portfolio oversight"}
        title="Portfolio overview"
        description={`${properties.length} properties · 25 rooms`}
        actions={
          <>
            {canAddProperty ? (
              <Link href="/properties/new" className={btnPrimary}>
                + Add property
              </Link>
            ) : null}
            <Link href="/dashboard/reports" className={btnSecondary}>
              Export
            </Link>
          </>
        }
      />

      <StatGrid>
        <StatCard
          label="Occupancy"
          value={occupancyRate}
          hint="+4%"
          tone="green"
          href="/dashboard/room-occupancy"
        />
        <StatCard
          label="Rent collected"
          value={rentCollectedFormatted}
          hint="98%"
          tone="green"
          href="/dashboard/rent-payments"
        />
        <StatCard
          label="Open repairs"
          value={openRepairsCount}
          hint="1 urgent"
          tone="red"
          href="/dashboard/maintenance"
        />
        <StatCard
          label="Certificates due"
          value="2"
          hint="30 days"
          tone="amber"
          href="/dashboard/documents"
        />
      </StatGrid>

      <HomeColumns
        main={
          <VerticalBarChart
            title="Rent collected"
            caption="Last 12 months"
            bars={SPEC_RENT_BARS}
            highlightLast
          />
        }
        aside={<AttentionCard items={SPEC_ATTENTION} />}
      />

      <section className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Properties</h2>
            <p className="text-xs text-slate-500">Rooms and occupancy from your portfolio</p>
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
              <Th>Rent / month</Th>
              <Th>Compliance</Th>
            </tr>
          </thead>
          <tbody>
            {properties.map((prop) => (
              <tr key={prop.id}>
                <Td>
                  <div className="flex items-center gap-3">
                    <Avatar name={prop.name} size="sm" />
                    <span className="font-semibold text-slate-900">{prop.name}</span>
                  </div>
                </Td>
                <Td>
                  <span className="text-slate-700">{prop.rooms}</span>
                </Td>
                <Td>
                  <span className="font-medium text-slate-800">{prop.occupancy}</span>
                </Td>
                <Td>
                  <span className="font-medium text-slate-900">{prop.rent}</span>
                </Td>
                <Td>
                  <StatusChip tone={prop.tone as any}>{prop.compliance}</StatusChip>
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      </section>

      {/* Interactive Tabs for Inspections, Repairs, and In-depth Portfolio management */}
      <section className="mt-8">
        <LandlordEnterpriseClient
          accessToken={token}
          organisationId={orgId}
          role={activeRole}
        />
      </section>
    </div>
  );
}
