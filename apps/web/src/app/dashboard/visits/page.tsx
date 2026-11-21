import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { WeekBoard, type WeekTone } from "@/components/ops/WeekBoard";
import { btnPrimary, btnSecondary, FilterTabs, humanize, inputClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchVisits } from "@/lib/opsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function visitTone(status: string): WeekTone {
  const value = status.toLowerCase();
  if (value.includes("cancel") || value.includes("miss") || value.includes("no_show")) return "red";
  if (value.includes("complete")) return "gray";
  if (value.includes("confirm")) return "indigo";
  return "blue";
}

function visitsHref(next: { q?: string; status?: string; week?: string; view?: string }) {
  const search = new URLSearchParams();
  if (next.q) search.set("q", next.q);
  if (next.status) search.set("status", next.status);
  if (next.week) search.set("week", next.week);
  if (next.view && next.view !== "week") search.set("view", next.view);
  const query = search.toString();
  return query ? `/dashboard/visits?${query}` : "/dashboard/visits";
}

export default async function VisitsPage({
  searchParams,
}: {
  searchParams?: Promise<{ week?: string; view?: string; q?: string; status?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/visits");
  const params = searchParams ? await searchParams : {};
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["visits.manage.assigned", "tenants.manage"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see visits." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Visits will be available once sign-in is configured." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/visits" />;
    const page = await fetchVisits({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    const q = (params.q ?? "").trim();
    const needle = q.toLowerCase();
    const statuses = [...new Set(page.items.map((visit) => visit.status).filter(Boolean))].sort();
    const status = statuses.includes(params.status ?? "") ? params.status ?? "" : "";
    const visible = page.items.filter((visit) => {
      if (status && visit.status !== status) return false;
      if (!needle) return true;
      return visit.purpose.toLowerCase().includes(needle) || visit.tenant_id.toLowerCase().includes(needle);
    });
    const filtered = Boolean(q || status);
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="My work"
          title="Visits"
          description="Plan and record tenant visits."
          actions={
            <Link href="/dashboard/visits/new" className={btnPrimary}>
              + Book visit
            </Link>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {status ? <input type="hidden" name="status" value={status} /> : null}
            {params.week ? <input type="hidden" name="week" value={params.week} /> : null}
            {params.view ? <input type="hidden" name="view" value={params.view} /> : null}
            <label className="sr-only" htmlFor="visit-search">
              Search visits
            </label>
            <input id="visit-search" name="q" defaultValue={q} placeholder="Search purpose or tenant reference" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: visitsHref({ q, week: params.week, view: params.view }), active: !status },
              ...statuses.map((item) => ({
                label: humanize(item),
                href: visitsHref({ q, status: item, week: params.week, view: params.view }),
                active: status === item,
              })),
            ]}
          />
        </div>
        {page.items.length === 0 ? (
          <EmptyState title="No visits yet" description="Scheduled visits will appear on the calendar." action={{ label: "Book visit", href: "/dashboard/visits/new" }} />
        ) : visible.length === 0 ? (
          <EmptyState
            title="No matching visits"
            description="Nothing on this page matches the search or status."
            action={filtered ? { label: "Clear filters", href: "/dashboard/visits" } : undefined}
          />
        ) : (
          <WeekBoard
            basePath="/dashboard/visits"
            anchor={params.week}
            view={params.view}
            query={{ q, status }}
            events={visible.map((visit) => ({
              id: visit.id,
              title: visit.purpose,
              start: visit.scheduled_at,
              tone: visitTone(visit.status),
            }))}
          />
        )}
        <p className="text-sm text-slate-500">
          {visible.length === 0 ? `Showing 0 of ${page.total}` : `Showing 1–${visible.length} of ${page.total}`}
        </p>
      </div>
    );
  } catch (error) {
    return <ErrorState description={error instanceof Error ? error.message : "We couldn't load visits. Please try again."} retryHref="/dashboard/visits" />;
  }
}
