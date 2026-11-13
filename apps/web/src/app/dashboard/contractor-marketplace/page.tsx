import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import {
  getContractorMarketplaceReports,
  listContractorWorkspaceJobs,
  searchContractorMarketplace,
} from "@/lib/contractorMarketplaceApi";

const READ = ["contractor_marketplace.read", "contractor_marketplace.manage", "contractor_marketplace.workspace"];

export default async function ContractorMarketplacePage() {
  const session = await requireAuthenticatedSession("/dashboard/contractor-marketplace");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

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
      <ErrorState description="Contractor marketplace is disabled until CONTRACTOR_MARKETPLACE_GLOBAL_ENABLED and organisation settings are approved." />
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Contractor marketplace (add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Only administrator-verified contractors appear in search. Quotations and completion require explicit approval.
        </p>
      </header>
      {admin ? (
        <section className="grid gap-4 sm:grid-cols-4">
          <Stat label="Registered" value={String(stats.contractors_total ?? "0")} />
          <Stat label="Approved" value={String(stats.contractors_approved ?? "0")} />
          <Stat label="Pending verification" value={String(stats.pending_verification ?? "0")} />
          <Stat label="Open jobs" value={String(stats.open_jobs ?? "0")} />
        </section>
      ) : null}
      {workspace ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="font-medium text-slate-800">My assigned jobs</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {workspaceJobs.length === 0 ? (
              <li className="py-2 text-slate-500">No assigned marketplace jobs.</li>
            ) : (
              workspaceJobs.map((j) => (
                <li key={String(j.id)} className="flex justify-between py-2">
                  <span>{String(j.reference_number)}</span>
                  <span className="text-slate-500">{String(j.status)}</span>
                </li>
              ))
            )}
          </ul>
        </section>
      ) : (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="font-medium text-slate-800">Approved contractors</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {contractors.length === 0 ? (
              <li className="py-2 text-slate-500">No approved contractors match your filters.</li>
            ) : (
              contractors.map((c) => (
                <li key={String(c.id)} className="flex justify-between py-2">
                  <span>{String(c.business_name)}</span>
                  <span className="text-slate-500">{String(c.verification_status)}</span>
                </li>
              ))
            )}
          </ul>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}
