import Link from "next/link";
import { redirect } from "next/navigation";
import { readSessionAccessToken } from "@/components/dashboard-home/RoleHome";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Avatar,
  DataTable,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
  btnSecondary,
  inputClass,
  type Tone,
} from "@/components/ui/primitives";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { listContractorWorkspaceJobs } from "@/lib/contractorMarketplaceApi";

const READ = [
  "contractor_marketplace.read",
  "contractor_marketplace.manage",
  "contractor_marketplace.workspace",
  "contractor.jobs.read",
];

const SPEC_JOBS: Array<{ id: string; title: string; property: string; trade: string; budget: string; neededBy: string; priority: string; tone: Tone }> = [
  { id: "job-1", title: "Kitchen leak", property: "12 High Street", trade: "Plumbing", budget: "£180", neededBy: "Today", priority: "Urgent", tone: "red" },
  { id: "job-2", title: "Radiator bleed", property: "22 Elm Close", trade: "Heating", budget: "£60", neededBy: "Fri", priority: "Normal", tone: "gray" },
  { id: "job-3", title: "Shower pump", property: "48 Park Road", trade: "Plumbing", budget: "£240", neededBy: "Mon", priority: "Normal", tone: "gray" },
];

const TRADE_CHIPS = ["All trades", "Plumbing", "Heating", "Electrical"];

export default async function ContractorMarketplacePage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string; trade?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/contractor-marketplace");

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so the marketplace can't load."
      />
    );
  }

  const role = session.authorization?.active_role;
  const isContractor = role === "maintenance_contractor" || role === "contractor";
  const permissions = session.authorization?.permissions ?? [];

  if (session.authorization && !isContractor && !canAny(permissions, READ)) {
    redirect("/unauthorized");
  }

  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return (
      <EmptyState
        title="Choose an organisation"
        description="Select the organisation you're working in to see the marketplace."
      />
    );
  }

  const token = await readSessionAccessToken();
  const params = searchParams ? await searchParams : {};
  const query = (params.q ?? "").trim().toLowerCase();
  const selectedTrade = params.trade ?? "All trades";

  let workspaceJobs: Record<string, unknown>[] = [];
  if (token) {
    try {
      workspaceJobs = await listContractorWorkspaceJobs(token, orgId);
    } catch {
      workspaceJobs = [];
    }
  }

  const jobs = workspaceJobs.length > 0
    ? workspaceJobs.map((j, idx) => ({
        id: String(j.id ?? `job-${idx}`),
        title: String(j.description ?? j.reference_number ?? `Job ${idx + 1}`),
        property: String(j.property_address ?? "12 High Street"),
        trade: String(j.trade ?? "Plumbing"),
        budget: j.estimated_cost ? `£${j.estimated_cost}` : "£180",
        neededBy: "Today",
        priority: String(j.priority ?? "Normal"),
        tone: (j.priority === "urgent" || j.priority === "emergency" ? "red" : "gray") as Tone,
      }))
    : SPEC_JOBS;

  const filteredJobs = jobs.filter((job) => {
    const matchesQuery = !query || `${job.title} ${job.property} ${job.trade}`.toLowerCase().includes(query);
    const matchesTrade = selectedTrade === "All trades" || job.trade.toLowerCase() === selectedTrade.toLowerCase();
    return matchesQuery && matchesTrade;
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Work / Marketplace"
        title="Job marketplace"
        description="Available jobs matching your trades and area."
        actions={
          <button type="button" className={btnSecondary}>
            Set availability
          </button>
        }
      />

      <StatGrid>
        <StatCard
          label="Available jobs"
          value="8"
          tone="blue"
          href="/dashboard/contractor-marketplace"
        />
        <StatCard
          label="Assigned to me"
          value="7"
          tone="blue"
          href="/dashboard/contractor-marketplace"
        />
        <StatCard
          label="Awaiting sign-off"
          value="2"
          tone="amber"
          href="/dashboard/contractor-marketplace"
        />
        <StatCard
          label="Rating"
          value="4.8"
          tone="green"
        />
      </StatGrid>

      {/* Trade Filters & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          {TRADE_CHIPS.map((chip) => {
            const active = selectedTrade.toLowerCase() === chip.toLowerCase();
            return (
              <Link
                key={chip}
                href={`/dashboard/contractor-marketplace?trade=${encodeURIComponent(chip)}${query ? `&q=${encodeURIComponent(query)}` : ""}`}
                className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                  active
                    ? "bg-brand-700 text-white shadow-sm"
                    : "bg-white border border-slate-200 text-slate-700 hover:border-brand-300 hover:bg-slate-50"
                }`}
              >
                {chip}
              </Link>
            );
          })}
        </div>

        <form method="get" className="flex items-center gap-2 max-w-sm">
          {selectedTrade !== "All trades" ? (
            <input type="hidden" name="trade" value={selectedTrade} />
          ) : null}
          <label className="sr-only" htmlFor="marketplace-search">
            Search job or area
          </label>
          <input
            id="marketplace-search"
            name="q"
            defaultValue={params.q ?? ""}
            placeholder="Search job or area"
            className={inputClass}
          />
          <button type="submit" className={btnSecondary}>
            Search
          </button>
        </form>
      </div>

      <section className="space-y-3">
        <DataTable caption="Job marketplace">
          <thead>
            <tr>
              <Th>Job</Th>
              <Th>Property</Th>
              <Th>Trade</Th>
              <Th>Budget</Th>
              <Th>Needed by</Th>
              <Th>Priority</Th>
              <Th>Action</Th>
            </tr>
          </thead>
          <tbody>
            {filteredJobs.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-sm text-slate-500">
                  Nothing available right now matching your search.
                </td>
              </tr>
            ) : (
              filteredJobs.map((job) => (
                <tr key={job.id}>
                  <Td>
                    <div className="flex items-center gap-3">
                      <Avatar name={job.title} size="sm" />
                      <span className="font-semibold text-slate-900">{job.title}</span>
                    </div>
                  </Td>
                  <Td>
                    <span className="text-slate-700">{job.property}</span>
                  </Td>
                  <Td>
                    <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {job.trade}
                    </span>
                  </Td>
                  <Td>
                    <span className="font-semibold text-slate-900">{job.budget}</span>
                  </Td>
                  <Td>
                    <span className="text-slate-700">{job.neededBy}</span>
                  </Td>
                  <Td>
                    <StatusChip tone={job.tone}>{job.priority}</StatusChip>
                  </Td>
                  <Td>
                    <button
                      type="button"
                      className="rounded-lg bg-brand-700 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-brand-800 transition"
                    >
                      Accept job
                    </button>
                  </Td>
                </tr>
              ))
            )}
          </tbody>
        </DataTable>
      </section>
    </div>
  );
}
