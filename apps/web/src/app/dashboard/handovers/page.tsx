import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, btnSecondary, DataTable, FilterTabs, humanize, inputClass, linkClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { fetchHandovers } from "@/lib/supportApi";
import { requireAuthenticatedSession } from "@/lib/session";

function shortId(value: string): string {
  return value.length > 10 ? `…${value.slice(-6)}` : value;
}

function formatCreated(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const time = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const startToday = new Date();
  startToday.setHours(0, 0, 0, 0);
  const startThat = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDiff = Math.round((startToday.getTime() - startThat.getTime()) / 86400000);
  if (dayDiff === 0) return `Today ${time}`;
  if (dayDiff === 1) return `Yesterday ${time}`;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function handoverHref(next: { box?: string; q?: string; status?: string }) {
  const search = new URLSearchParams();
  if (next.box && next.box !== "to") search.set("box", next.box);
  if (next.q) search.set("q", next.q);
  if (next.status) search.set("status", next.status);
  const query = search.toString();
  return query ? `/dashboard/handovers?${query}` : "/dashboard/handovers";
}

export default async function HandoversPage({
  searchParams,
}: {
  searchParams?: Promise<{ box?: string; q?: string; status?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/handovers");
  const params = searchParams ? await searchParams : {};
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "support_notes.read.assigned",
      "tenants.manage",
      "tenants.read",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see handovers." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Handovers will be available once sign-in is configured." />;
  }

  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) {
      return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/handovers" />;
    }
    const page = await fetchHandovers({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    const userId = session.authorization?.user_id;
    const box = params.box === "from" || params.box === "all" ? params.box : "to";
    const query = (params.q ?? "").trim().toLowerCase();
    const statuses = [...new Set(page.items.map((item) => item.status).filter(Boolean))].sort();
    const status = statuses.includes(params.status ?? "") ? params.status ?? "" : "";
    const items = page.items.filter((item) => {
      if (box === "to" && userId && item.recipient_user_id !== userId) return false;
      if (box === "from" && userId && item.created_by_user_id !== userId) return false;
      if (status && item.status !== status) return false;
      if (!query) return true;
      return item.summary.toLowerCase().includes(query) || item.tenant_id.toLowerCase().includes(query);
    });
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="My work"
          title="Handovers"
          description="What the next person needs to know."
          actions={
            <Link href="/dashboard/handovers/new" className={btnPrimary}>
              + New handover
            </Link>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {box !== "to" ? <input type="hidden" name="box" value={box} /> : null}
            {status ? <input type="hidden" name="status" value={status} /> : null}
            <label className="sr-only" htmlFor="handover-search">
              Search tenant or staff
            </label>
            <input id="handover-search" name="q" defaultValue={params.q ?? ""} placeholder="Search tenant or staff" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "To me", href: handoverHref({ q: params.q }), active: box === "to" },
              { label: "From me", href: handoverHref({ box: "from", q: params.q }), active: box === "from" },
              { label: "All", href: handoverHref({ box: "all", q: params.q }), active: box === "all" },
              ...statuses.map((item) => ({
                label: humanize(item),
                href: handoverHref({ box, q: params.q, status: item }),
                active: status === item,
              })),
            ]}
          />
        </div>
        {items.length === 0 ? (
          <EmptyState
            title="No handovers"
            description={query || box !== "all" ? "Nothing matches this view." : "Submitted handovers will appear here."}
            action={query || box !== "all" ? { label: "Clear filters", href: "/dashboard/handovers?box=all" } : undefined}
          />
        ) : (
          <DataTable caption="Handovers">
            <thead>
              <tr>
                <Th>Tenant</Th>
                <Th>From</Th>
                <Th>Summary</Th>
                <Th>Created</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/60">
                  <Td className="font-mono text-xs text-slate-700">{shortId(item.tenant_id)}</Td>
                  <Td className="font-mono text-xs">{shortId(item.created_by_user_id)}</Td>
                  <Td>
                    <Link href={`/dashboard/handovers/${item.id}`} className={linkClass}>
                      {item.summary}
                    </Link>
                  </Td>
                  <Td>
                    {formatCreated(item.handover_at)}
                  </Td>
                  <Td>
                    <StatusChip status={item.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <p className="text-sm text-slate-500">
          {items.length === 0 ? `Showing 0 of ${page.total}` : `Showing 1–${items.length} of ${page.total}`}
        </p>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "We couldn't load handovers. Please try again."} retryHref="/dashboard/handovers" />
    );
  }
}
