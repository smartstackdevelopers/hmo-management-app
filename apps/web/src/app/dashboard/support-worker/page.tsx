import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { CaseloadClient } from "@/components/support/CaseloadClient";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchCaseload } from "@/lib/supportApi";
import { requireDashboardRole } from "@/lib/session";

export default async function SupportWorkerDashboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const session = await requireDashboardRole("support_worker", "/dashboard/support-worker");
  const params = searchParams ? await searchParams : {};

  if (!session.authConfigured) {
    return (
      <EmptyState
        title="Auth0 not configured"
        description="Support Worker caseload requires Auth0 environment variables."
      />
    );
  }

  if (!session.authorization) {
    return (
      <ErrorState description="Authorization snapshot unavailable. Confirm API connectivity and membership." />
    );
  }

  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return (
      <EmptyState
        title="Organisation required"
        description="Select an organisation membership to view your assigned caseload."
      />
    );
  }

  let caseloadError: string | null = null;
  let items: Awaited<ReturnType<typeof fetchCaseload>>["items"] = [];
  let total = 0;

  if (isAuth0Configured() && auth0) {
    try {
      const tokenResult = await auth0.getAccessToken();
      const token = tokenResult?.token;
      if (token) {
        const page = await fetchCaseload({
          accessToken: token,
          organisationId: orgId,
          role: session.authorization.active_role,
          q: params.q,
        });
        items = page.items;
        total = page.total;
      } else {
        caseloadError = "Access token unavailable.";
      }
    } catch (error) {
      caseloadError = error instanceof Error ? error.message : "Failed to load caseload.";
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        eyebrow="Support"
        title="My caseload"
        description="Assigned tenants only. Daily logs and handovers stay within your organisation and assignment scope."
      />

      <div className="flex flex-wrap gap-3 text-sm">
        <Link
          href="/dashboard/handovers"
          className="rounded-md border border-slate-200 bg-white px-3 py-2 text-forest-900 hover:border-teal-700"
        >
          Handovers
        </Link>
        <Link
          href="/dashboard/daily-logs/new"
          className="rounded-md bg-teal-700 px-3 py-2 text-white hover:bg-teal-800"
        >
          New daily log
        </Link>
      </div>

      {caseloadError ? <ErrorState description={caseloadError} /> : null}

      {!caseloadError && items.length === 0 ? (
        <EmptyState
          title="No assigned tenants"
          description="Ask an Organisation Admin to create a case assignment for you."
        />
      ) : null}

      {items.length > 0 ? (
        <CaseloadClient initialItems={items} total={total} initialQuery={params.q ?? ""} />
      ) : null}
    </div>
  );
}
