import Link from "next/link";
import {
  AttentionCard,
  HomeColumns,
  ModuleTiles,
  plural,
  readSessionAccessToken,
  visibleModuleIds,
  type AttentionEntry,
} from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Avatar,
  DataTable,
  SeriesChart,
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
import { fetchPlatformOrganisations, type PlatformOrganisation } from "@/lib/platformGovernanceApi";
import { requireDashboardRole } from "@/lib/session";

const ORGANISATIONS_HREF = "/dashboard/super-admin/organisations";

export default async function SuperAdminDashboardPage() {
  const session = await requireDashboardRole("super_admin", "/dashboard/super-admin");

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so the platform overview can't load."
      />
    );
  }

  if (!session.authorization) {
    return (
      <ErrorState
        title="We couldn't load your access"
        description="Your role and permissions didn't load. Please try again in a moment."
        retryHref="/dashboard/super-admin"
      />
    );
  }

  const { permissions, active_role: role, active_organisation_id: orgId } = session.authorization;
  const homeSession = { permissions, role };
  const visible = visibleModuleIds(homeSession);

  let organisations: PlatformOrganisation[] | null = null;
  if (orgId) {
    try {
      const token = await readSessionAccessToken();
      if (token) {
        organisations = await fetchPlatformOrganisations({
          accessToken: token,
          organisationId: orgId,
          role: role ?? "super_admin",
        });
      }
    } catch {
      organisations = null;
    }
  }

  const activeCount = organisations?.filter((org) => org.status.toLowerCase() === "active").length ?? 0;
  const notActive = organisations?.filter((org) => org.status.toLowerCase() !== "active") ?? [];
  const attention: AttentionEntry[] = notActive.slice(0, 5).map((org) => ({
    key: org.id,
    title: org.name,
    meta: `Status: ${humanize(org.status)}`,
    tone: toneForStatus(org.status),
    href: ORGANISATIONS_HREF,
  }));

  const statusPoints = organisations
    ? [...organisations.reduce((counts, org) => {
        const key = humanize(org.status) || "Unknown";
        counts.set(key, (counts.get(key) ?? 0) + 1);
        return counts;
      }, new Map<string, number>())].map(([label, value]) => ({ label, value }))
    : [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Super Admin"
        title="Platform overview"
        description={
          organisations
            ? `${plural(organisations.length, "organisation")} on HMore.`
            : "Organisations, people and platform health across HMore."
        }
        actions={
          <>
            {visible.has("organisations") ? (
              <Link href={ORGANISATIONS_HREF} className={btnPrimary}>
                + New organisation
              </Link>
            ) : null}
            {visible.has("reports") ? (
              <Link href="/dashboard/reports" className={btnSecondary}>
                Export
              </Link>
            ) : null}
          </>
        }
      />

      {organisations ? (
        <StatGrid>
          <StatCard label="Organisations" value={organisations.length} href={ORGANISATIONS_HREF} />
          <StatCard label="Active" value={activeCount} tone="green" hint={activeCount > 0 ? "Live" : undefined} />
          <StatCard
            label="Not yet active"
            value={notActive.length}
            tone="amber"
            hint={notActive.length > 0 ? "Review" : undefined}
            href={ORGANISATIONS_HREF}
          />
        </StatGrid>
      ) : null}

      <HomeColumns
        main={
          statusPoints.length > 0 ? (
            <SeriesChart title="Organisations" caption="By status" points={statusPoints} />
          ) : undefined
        }
        aside={<AttentionCard items={attention} />}
      />

      <section className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-base font-semibold text-slate-900">Organisations</h2>
          <Link href={ORGANISATIONS_HREF} className={linkClass}>
            View all
          </Link>
        </div>
        {organisations === null ? (
          <p className="text-sm text-slate-500">
            We couldn&apos;t load organisations just now. Open the organisations page to try again.
          </p>
        ) : organisations.length === 0 ? (
          <p className="text-sm text-slate-500">No organisations yet. Create the first one to get started.</p>
        ) : (
          <>
            <DataTable caption="Organisations">
              <thead>
                <tr>
                  <Th>Organisation</Th>
                  <Th>Slug</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {organisations.slice(0, 6).map((org) => (
                  <tr key={org.id}>
                    <Td>
                      <div className="flex items-center gap-3">
                        <Avatar name={org.name} size="sm" />
                        <span className="font-semibold text-slate-900">{org.name}</span>
                      </div>
                    </Td>
                    <Td>{org.slug}</Td>
                    <Td>
                      <StatusChip status={org.status} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
            <p className="px-1 text-xs text-slate-400">
              Showing 1–{Math.min(6, organisations.length)} of {organisations.length}
            </p>
          </>
        )}
      </section>

      <ModuleTiles
        session={homeSession}
        title="Platform tools"
        ids={[
          "organisations",
          "platform-admin",
          "governance",
          "audit",
          "privacy",
          "backups",
          "performance",
          "integrations",
          "integration-hub",
          "ai-costs",
          "ai-feature-flags",
          "reports",
        ]}
        extra={[
          {
            href: "/dashboard/approvals/registrations",
            title: "Registration requests",
            description: "Approve or decline people asking to join.",
          },
        ]}
      />
    </div>
  );
}
