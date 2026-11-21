import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { WeekBoard, type WeekTone } from "@/components/ops/WeekBoard";
import { btnPrimary, btnSecondary, FilterTabs, humanize, inputClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchShifts } from "@/lib/opsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function shiftTone(shiftType: string, status: string): WeekTone {
  const value = `${shiftType} ${status}`.toLowerCase();
  if (value.includes("uncovered") || value.includes("gap") || value.includes("cancel")) return "red";
  if (value.includes("meeting")) return "amber";
  if (value.includes("on_call") || value.includes("on-call")) return "gray";
  if (value.includes("early") || value.includes("late")) return "indigo";
  return "blue";
}

function rotaHref(next: { q?: string; status?: string; week?: string; view?: string }) {
  const search = new URLSearchParams();
  if (next.q) search.set("q", next.q);
  if (next.status) search.set("status", next.status);
  if (next.week) search.set("week", next.week);
  if (next.view && next.view !== "week") search.set("view", next.view);
  const query = search.toString();
  return query ? `/dashboard/rota?${query}` : "/dashboard/rota";
}

export default async function RotaPage({
  searchParams,
}: {
  searchParams?: Promise<{ week?: string; view?: string; q?: string; status?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/rota");
  const params = searchParams ? await searchParams : {};
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "organisation.users.manage",
      "organisation.users.read",
      "visits.manage.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see the rota." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="The rota will be available once sign-in is configured." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/rota" />;
    const canCreate = Boolean(session.authorization?.permissions?.includes("organisation.users.manage"));
    const page = await fetchShifts({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    const q = (params.q ?? "").trim();
    const needle = q.toLowerCase();
    const statuses = [...new Set(page.items.map((shift) => shift.status).filter(Boolean))].sort();
    const status = statuses.includes(params.status ?? "") ? params.status ?? "" : "";
    const visible = page.items.filter((shift) => {
      if (status && shift.status !== status) return false;
      if (!needle) return true;
      return (
        shift.shift_type.toLowerCase().includes(needle) ||
        shift.status.toLowerCase().includes(needle) ||
        shift.staff_user_id.toLowerCase().includes(needle) ||
        (shift.location ?? "").toLowerCase().includes(needle)
      );
    });
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="People"
          title="Staff rota"
          description="Plan shifts and cover gaps early."
          actions={
            <>
              <Link href="/dashboard/visits" className={btnSecondary}>
                Visits
              </Link>
              {canCreate ? (
                <Link href="/dashboard/rota/new" className={btnPrimary}>
                  + Add shift
                </Link>
              ) : null}
            </>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {status ? <input type="hidden" name="status" value={status} /> : null}
            {params.week ? <input type="hidden" name="week" value={params.week} /> : null}
            {params.view ? <input type="hidden" name="view" value={params.view} /> : null}
            <label className="sr-only" htmlFor="rota-search">
              Search shifts
            </label>
            <input id="rota-search" name="q" defaultValue={q} placeholder="Search shift type or staff reference" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: rotaHref({ q, week: params.week, view: params.view }), active: !status },
              ...statuses.map((item) => ({
                label: humanize(item),
                href: rotaHref({ q, status: item, week: params.week, view: params.view }),
                active: status === item,
              })),
            ]}
          />
        </div>
        {page.items.length === 0 ? (
          <EmptyState
            title="No shifts yet"
            description="Shifts you add will appear on the week view."
            action={canCreate ? { label: "Add shift", href: "/dashboard/rota/new" } : undefined}
          />
        ) : visible.length === 0 ? (
          <EmptyState title="No matching shifts" description="Nothing on this page matches the search or status." action={{ label: "Clear filters", href: "/dashboard/rota" }} />
        ) : (
          <WeekBoard
            basePath="/dashboard/rota"
            anchor={params.week}
            view={params.view}
            query={{ q, status }}
            events={visible.map((shift) => ({
              id: shift.id,
              title: [humanize(shift.shift_type), shift.location?.trim()].filter(Boolean).join(" · "),
              start: shift.starts_at,
              end: shift.ends_at,
              tone: shiftTone(shift.shift_type, shift.status),
            }))}
          />
        )}
        <p className="text-sm text-slate-500">
          {visible.length === 0 ? `Showing 0 of ${page.total}` : `Showing 1–${visible.length} of ${page.total}`}
        </p>
      </div>
    );
  } catch (error) {
    return <ErrorState description={error instanceof Error ? error.message : "We couldn't load the rota. Please try again."} retryHref="/dashboard/rota" />;
  }
}
