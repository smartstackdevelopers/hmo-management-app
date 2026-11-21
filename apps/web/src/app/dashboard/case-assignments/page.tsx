import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { AssignmentForm } from "@/components/support/AssignmentForm";
import { Avatar, btnPrimary, btnSecondary, DataTable, FilterTabs, humanize, inputClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { organisationRequestHeaders } from "@/lib/organisation";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import type { CaseAssignment } from "@/lib/supportApi";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const STATUSES = ["active", "ended", "suspended"] as const;

function assignmentsHref(next: { q?: string; status?: string; page?: number }) {
  const search = new URLSearchParams();
  if (next.q) search.set("q", next.q);
  if (next.status) search.set("status", next.status);
  if (next.page && next.page > 1) search.set("page", String(next.page));
  const query = search.toString();
  return query ? `/dashboard/case-assignments?${query}` : "/dashboard/case-assignments";
}

export default async function CaseAssignmentsPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string; status?: string; page?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
  const session = await requireAuthenticatedSession("/dashboard/case-assignments");
  if (session.authorization && !can(session.authorization.permissions, "tenants.manage")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return (
      <EmptyState
        title="Choose an organisation"
        description="Select the organisation you're working in to manage case assignments."
      />
    );
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Case assignments will be available once sign-in is configured." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/case-assignments" />;
  }

  const q = (params.q ?? "").trim();
  const status = STATUSES.includes(params.status as (typeof STATUSES)[number]) ? params.status ?? "" : "";
  const pageNumber = Math.max(1, Number(params.page ?? "1") || 1);
  let items: CaseAssignment[] = [];
  let total = 0;
  let listError: string | null = null;
  try {
    const search = new URLSearchParams();
    search.set("page", String(pageNumber));
    search.set("page_size", "25");
    search.set("status", status);
    if (q) search.set("q", q);
    const response = await fetch(`${API_BASE}/api/v1/caseload?${search.toString()}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        ...organisationRequestHeaders({
          organisationId: orgId,
          role: session.authorization?.active_role,
        }),
      },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const body = (await response.json()) as { items: CaseAssignment[]; total: number };
    items = body.items ?? [];
    total = typeof body.total === "number" ? body.total : items.length;
  } catch (error) {
    listError = error instanceof Error ? error.message : "We couldn't load assignments.";
  }
  const from = items.length === 0 ? 0 : (pageNumber - 1) * 25 + 1;
  const to = items.length === 0 ? 0 : (pageNumber - 1) * 25 + items.length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="People"
        title="Case assignments"
        description="Match tenants to support workers and balance caseloads."
        actions={
          <a href="#assign-tenant" className={btnPrimary}>
            + Assign tenant
          </a>
        }
      />
      <div className="flex flex-wrap items-center gap-3">
        <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
          {status ? <input type="hidden" name="status" value={status} /> : null}
          <label className="sr-only" htmlFor="assignment-search">
            Search tenants
          </label>
          <input id="assignment-search" name="q" defaultValue={q} placeholder="Search tenant name or reference" className={inputClass} />
          <button type="submit" className={btnSecondary}>
            Search
          </button>
        </form>
        <FilterTabs
          tabs={[
            { label: "All", href: assignmentsHref({ q }), active: !status },
            ...STATUSES.map((item) => ({
              label: humanize(item),
              href: assignmentsHref({ q, status: item }),
              active: status === item,
            })),
          ]}
        />
      </div>
      {listError ? (
        <ErrorState description={listError} retryHref="/dashboard/case-assignments" />
      ) : items.length === 0 ? (
        <EmptyState
          title="No assignments"
          description={q || status ? "No assignments match this search or status." : "Assign a support worker and the case will appear here."}
          action={q || status ? { label: "Clear filters", href: "/dashboard/case-assignments" } : undefined}
        />
      ) : (
        <DataTable caption="Case assignments">
          <thead>
            <tr>
              <Th>Tenant</Th>
              <Th>Key worker</Th>
              <Th>Assigned</Th>
              <Th className="text-right">Logs</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const name = item.tenant_preferred_name || item.tenant_full_name || "";
              const worker = item.support_worker_display_name || "";
              return (
                <tr key={item.id} className="hover:bg-slate-50/60">
                  <Td>
                    <div className="flex items-center gap-3">
                      <Avatar name={name || "?"} size="sm" />
                      <Link href={`/dashboard/caseload/${item.tenant_id}`} className="font-semibold text-brand-700 hover:underline">
                        {name || "—"}
                      </Link>
                    </div>
                  </Td>
                  <Td>
                    <div className="flex items-center gap-3">
                      <Avatar name={worker || "?"} size="sm" />
                      <span>{worker || "—"}</span>
                    </div>
                  </Td>
                  <Td>{item.assigned_at ? new Date(item.assigned_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "—"}</Td>
                  <Td className="text-right tabular-nums">{item.recent_log_count ?? "—"}</Td>
                  <Td>
                    <StatusChip status={item.status} />
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
        <p>{items.length === 0 ? `Showing 0 of ${total}` : `Showing ${from}–${to} of ${total}`}</p>
        <div className="flex gap-2">
          {pageNumber > 1 ? (
            <Link className={btnSecondary} href={assignmentsHref({ q, status, page: pageNumber - 1 })}>
              Previous
            </Link>
          ) : null}
          {to < total ? (
            <Link className={btnSecondary} href={assignmentsHref({ q, status, page: pageNumber + 1 })}>
              Next
            </Link>
          ) : null}
        </div>
      </div>
      <div id="assign-tenant">
        <AssignmentForm
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
        />
      </div>
    </div>
  );
}
