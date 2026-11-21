import Link from "next/link";
import { redirect } from "next/navigation";
import { SafeguardingActions } from "@/components/compliance/SafeguardingActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, btnSecondary, DataTable, FilterTabs, humanize, inputClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchSafeguardingReminders } from "@/lib/complianceApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function safeguardingHref(next: { view?: string; status?: string; q?: string }) {
  const search = new URLSearchParams();
  if (next.view) search.set("view", next.view);
  if (next.status) search.set("status", next.status);
  if (next.q) search.set("q", next.q);
  const query = search.toString();
  return query ? `/dashboard/safeguarding?${query}` : "/dashboard/safeguarding";
}

export default async function SafeguardingPage({
  searchParams,
}: {
  searchParams?: Promise<{ view?: string; status?: string; q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/safeguarding");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "safeguarding.reminders.manage",
      "safeguarding.reminders.manage.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see safeguarding reminders." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Safeguarding reminders will be available once sign-in is configured." />;
  }
  const params = searchParams ? await searchParams : {};
  const overdueOnly = params.view === "overdue";
  const q = (params.q ?? "").trim();
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/safeguarding" />;
    const page = await fetchSafeguardingReminders({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      overdueOnly,
    });
    const statuses = [...new Set(page.items.map((row) => row.status).filter(Boolean))].sort();
    const status = statuses.includes(params.status ?? "") ? params.status ?? "" : "";
    const needle = q.toLowerCase();
    const visible = page.items.filter((row) => {
      if (status && row.status !== status) return false;
      if (!needle) return true;
      return (
        row.title.toLowerCase().includes(needle) ||
        row.category.toLowerCase().includes(needle) ||
        (row.tenant_id ?? "").toLowerCase().includes(needle)
      );
    });
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Safety"
          title="Safeguarding reminders"
          description="Follow-up tracking only. Keep titles free of confidential case detail."
          actions={
            <Link href="/dashboard/safeguarding/new" className={btnPrimary}>
              + New reminder
            </Link>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {overdueOnly ? <input type="hidden" name="view" value="overdue" /> : null}
            {status ? <input type="hidden" name="status" value={status} /> : null}
            <label className="sr-only" htmlFor="safeguarding-search">
              Search reminders
            </label>
            <input id="safeguarding-search" name="q" defaultValue={q} placeholder="Search reminders" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: safeguardingHref({ q }), active: !overdueOnly && !status },
              { label: "Overdue", href: safeguardingHref({ view: "overdue", q }), active: overdueOnly && !status },
              ...statuses.map((item) => ({
                label: humanize(item),
                href: safeguardingHref({ view: overdueOnly ? "overdue" : undefined, q, status: item }),
                active: status === item,
              })),
              { label: "Training", href: "/dashboard/training" },
            ]}
          />
        </div>
        {visible.length === 0 ? (
          <EmptyState
            title={overdueOnly ? "Nothing overdue" : "No reminders"}
            description={q || status ? "Nothing matches this search or status." : "Create a reminder when a follow-up needs a date."}
            action={q || status || overdueOnly ? { label: "Show all", href: "/dashboard/safeguarding" } : undefined}
          />
        ) : (
          <DataTable caption="Safeguarding reminders">
            <thead>
              <tr>
                <Th>Reminder</Th>
                <Th>Priority</Th>
                <Th>Due</Th>
                <Th>Status</Th>
                <Th>
                  <span className="sr-only">Actions</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/60">
                  <Td>
                    <p className="font-semibold text-slate-900">{row.title}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{row.category}</p>
                  </Td>
                  <Td>
                    <StatusChip status={row.priority} />
                  </Td>
                  <Td>{new Date(row.due_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</Td>
                  <Td>
                    <StatusChip status={row.status} />
                  </Td>
                  <Td>
                    <SafeguardingActions
                      reminderId={row.id}
                      status={row.status}
                      accessToken={token}
                      organisationId={orgId}
                      role={session.authorization?.active_role}
                    />
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
      <ErrorState
        description={error instanceof Error ? error.message : "We couldn't load safeguarding reminders. Please try again."}
        retryHref="/dashboard/safeguarding"
      />
    );
  }
}
