import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, btnSecondary, DataTable, FilterTabs, inputClass, linkClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchIncidents } from "@/lib/incidentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const FILTERS = [
  { label: "All", value: "" },
  { label: "Draft", value: "draft" },
  { label: "Submitted", value: "submitted" },
  { label: "Under review", value: "under_review" },
  { label: "Action required", value: "action_required" },
  { label: "Resolved", value: "resolved" },
  { label: "Closed", value: "closed" },
  { label: "Reopened", value: "reopened" },
] as const;

function incidentsHref(next: { status?: string; q?: string }) {
  const search = new URLSearchParams();
  if (next.status) search.set("status", next.status);
  if (next.q) search.set("q", next.q);
  const query = search.toString();
  return query ? `/dashboard/incidents?${query}` : "/dashboard/incidents";
}

export default async function IncidentsPage({
  searchParams,
}: {
  searchParams?: Promise<{ status?: string; q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/incidents");
  const params = searchParams ? await searchParams : {};
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "incidents.manage",
      "incidents.read.assigned",
      "incidents.create.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see incidents." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Incidents will be available once sign-in is configured." />;
  }
  const status = FILTERS.some((item) => item.value === params.status) ? params.status ?? "" : "";
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/incidents" />;
    const page = await fetchIncidents({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      status: status || undefined,
    });
    const canCreate = canAny(session.authorization?.permissions, ["incidents.manage", "incidents.create.assigned"]);
    const q = (params.q ?? "").trim();
    const needle = q.toLowerCase();
    const visible = page.items.filter((row) => {
      if (!needle) return true;
      return (
        row.title.toLowerCase().includes(needle) ||
        row.reference_number.toLowerCase().includes(needle) ||
        row.category.toLowerCase().includes(needle)
      );
    });
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Operations"
          title="Incidents"
          description="Record, review and learn from incidents."
          actions={
            <>
              <Link href="/dashboard/workload" className={btnSecondary}>
                Workload
              </Link>
              {canCreate ? (
                <Link href="/dashboard/incidents/new" className={btnPrimary}>
                  + Report incident
                </Link>
              ) : null}
            </>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {status ? <input type="hidden" name="status" value={status} /> : null}
            <label className="sr-only" htmlFor="incident-search">
              Search incidents
            </label>
            <input id="incident-search" name="q" defaultValue={q} placeholder="Search title or reference" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={FILTERS.map((item) => ({
              label: item.label,
              href: incidentsHref({ status: item.value, q }),
              active: status === item.value,
            }))}
          />
        </div>
        {visible.length === 0 ? (
          <EmptyState
            title="No incidents"
            description={status || q ? "No incidents match this search or status." : "Reported incidents will appear here."}
            action={status || q ? { label: "Clear filter", href: "/dashboard/incidents" } : undefined}
          />
        ) : (
          <DataTable caption="Incidents">
            <thead>
              <tr>
                <Th>Incident</Th>
                <Th>Category</Th>
                <Th>When</Th>
                <Th>Severity</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/60">
                  <Td>
                    <Link href={`/dashboard/incidents/${row.id}`} className={linkClass}>
                      {row.title}
                    </Link>
                    <p className="mt-0.5 font-mono text-xs text-slate-500">{row.reference_number}</p>
                  </Td>
                  <Td>{row.category}</Td>
                  <Td>{new Date(row.occurred_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</Td>
                  <Td>
                    <StatusChip status={row.severity} />
                  </Td>
                  <Td>
                    <StatusChip status={row.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <p className="text-sm text-slate-500">
          {visible.length === 0 ? `Showing 0 of ${page.total}` : `Showing 1–${visible.length} of ${page.total}`}
        </p>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "We couldn't load incidents. Please try again."} retryHref="/dashboard/incidents" />
    );
  }
}
