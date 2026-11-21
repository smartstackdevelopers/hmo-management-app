import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Avatar, DataTable, StatCard, StatGrid, StatusChip, Td, Th, btnSecondary, inputClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import {
  getContractorMarketplaceReports,
  listContractorWorkspaceJobs,
  searchContractorMarketplace,
} from "@/lib/contractorMarketplaceApi";

const READ = ["contractor_marketplace.read", "contractor_marketplace.manage", "contractor_marketplace.workspace"];

export default async function ContractorMarketplacePage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/contractor-marketplace");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see the marketplace." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so the marketplace can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/contractor-marketplace" />;
  }

  const params = searchParams ? await searchParams : {};
  const query = (params.q ?? "").trim().toLowerCase();
  const perms = session.authorization?.permissions ?? [];
  const workspace = perms.includes("contractor_marketplace.workspace");
  const admin = perms.includes("contractor_marketplace.manage") || perms.includes("contractor_marketplace.reports");

  let stats: Record<string, unknown> = {};
  let contractors: Record<string, unknown>[] = [];
  let workspaceJobs: Record<string, unknown>[] = [];

  try {
    if (admin) {
      stats = await getContractorMarketplaceReports(token, orgId);
    }
    if (!workspace) {
      contractors = await searchContractorMarketplace(token, orgId);
    } else {
      workspaceJobs = await listContractorWorkspaceJobs(token, orgId);
    }
  } catch {
    return (
      <ErrorState
        title="Marketplace unavailable"
        description="The job marketplace isn't switched on for this organisation yet."
        retryHref="/dashboard/contractor-marketplace"
      />
    );
  }

  const visibleJobs = workspaceJobs.filter(
    (job) => !query || `${job.description ?? ""} ${job.reference_number ?? ""}`.toLowerCase().includes(query),
  );
  const visibleContractors = contractors.filter(
    (contractor) => !query || String(contractor.business_name ?? "").toLowerCase().includes(query),
  );
  const shown = workspace ? visibleJobs : visibleContractors;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow={workspace ? "Work / Marketplace" : "Operations / Marketplace"}
        title={workspace ? "Job marketplace" : "Contractor marketplace"}
        description={
          workspace
            ? "Jobs assigned to you. Start a job from its reference when the record is open."
            : "Verified contractors in this organisation. Quotations and completion still need an explicit approval."
        }
      />
      <form method="get" className="flex max-w-xl items-center gap-2">
        <label className="sr-only" htmlFor="marketplace-search">
          Search jobs or contractors
        </label>
        <input
          id="marketplace-search"
          name="q"
          defaultValue={params.q ?? ""}
          placeholder={workspace ? "Search job or reference" : "Search contractors"}
          className={inputClass}
        />
        <button type="submit" className={btnSecondary}>
          Search
        </button>
      </form>
      {admin ? (
        <StatGrid>
          <StatCard label="Registered" value={String(stats.contractors_total ?? "0")} />
          <StatCard label="Approved" value={String(stats.contractors_approved ?? "0")} tone="green" />
          <StatCard
            label="Pending verification"
            value={String(stats.pending_verification ?? "0")}
            tone="amber"
            hint={Number(stats.pending_verification ?? 0) > 0 ? "Review" : undefined}
          />
          <StatCard label="Open jobs" value={String(stats.open_jobs ?? "0")} />
        </StatGrid>
      ) : null}
      {workspace ? (
        visibleJobs.length === 0 ? (
          <EmptyState
            title={query ? "No matching jobs" : "No assigned jobs"}
            description={query ? "Nothing assigned to you matches that search." : "Jobs assigned to you will appear here."}
            action={query ? { label: "Clear search", href: "/dashboard/contractor-marketplace" } : undefined}
          />
        ) : (
          <DataTable caption="Assigned marketplace jobs">
            <thead>
              <tr>
                <Th>Job</Th>
                <Th>Reference</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {visibleJobs.map((job) => (
                <tr key={String(job.id)} className="hover:bg-slate-50">
                  <Td>
                    <span className="flex items-center gap-3">
                      <Avatar name={String(job.reference_number || "Job")} size="sm" />
                      <span className="font-semibold text-slate-900">{String(job.description || "Job")}</span>
                    </span>
                  </Td>
                  <Td>{String(job.reference_number || "—")}</Td>
                  <Td>
                    <StatusChip status={String(job.status)} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )
      ) : visibleContractors.length === 0 ? (
        <EmptyState
          title={query ? "No matching contractors" : "No approved contractors"}
          description={query ? "No verified contractor matches that search." : "Verified contractors will appear here."}
          action={query ? { label: "Clear search", href: "/dashboard/contractor-marketplace" } : undefined}
        />
      ) : (
        <DataTable caption="Approved contractors">
          <thead>
            <tr>
              <Th>Business</Th>
              <Th>Verification</Th>
            </tr>
          </thead>
          <tbody>
            {visibleContractors.map((contractor) => (
              <tr key={String(contractor.id)} className="hover:bg-slate-50">
                <Td>
                  <span className="flex items-center gap-3">
                    <Avatar name={String(contractor.business_name || "Contractor")} size="sm" />
                    <span className="font-semibold text-slate-900">{String(contractor.business_name)}</span>
                  </span>
                </Td>
                <Td>
                  <StatusChip status={String(contractor.verification_status)} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {shown.length === 0 ? "0" : `1–${shown.length}`} of {workspace ? workspaceJobs.length : contractors.length}
      </p>
    </div>
  );
}
