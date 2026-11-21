import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Avatar,
  DataTable,
  FilterTabs,
  StatusChip,
  Td,
  Th,
  btnPrimary,
  btnSecondary,
  humanize,
  inputClass,
} from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchApplications } from "@/lib/housingApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const UK_TIME_ZONE = "Europe/London";

const VIEWS = [
  { id: "all", label: "All" },
  { id: "submitted", label: "Submitted" },
  { id: "evidence", label: "Evidence needed" },
  { id: "pending", label: "Pending approvals" },
] as const;

function shortDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: UK_TIME_ZONE }).format(date);
}

function hrefFor(view: string, q?: string) {
  const search = new URLSearchParams();
  if (view && view !== "all") search.set("view", view);
  if (q) search.set("q", q);
  const query = search.toString();
  return query ? `/dashboard/housing-applications?${query}` : "/dashboard/housing-applications";
}

export default async function HousingApplicationsPage({
  searchParams,
}: {
  searchParams?: Promise<{ view?: string; q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/housing-applications");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "applications.manage",
      "applications.review",
      "applications.read.own",
      "applications.read.assigned",
      "applications.create.own",
      "applications.create.assigned",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see applications." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so applications can't load."
      />
    );
  }
  const params = searchParams ? await searchParams : {};
  const view = VIEWS.some((item) => item.id === params.view) ? params.view! : "all";
  const q = params.q?.trim() || undefined;
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) {
      return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/housing-applications" />;
    }
    const page = await fetchApplications({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      pendingApprovals: view === "pending",
      status: view === "submitted" ? "submitted" : view === "evidence" ? "information_required" : undefined,
      q,
    });
    const from = page.items.length === 0 ? 0 : 1;
    const to = page.items.length;
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Housing / Applications"
          title="Housing applications"
          description="Applications, evidence packs and decisions."
          actions={
            <Link href="/dashboard/housing-applications/new" className={btnPrimary}>
              + New application
            </Link>
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {view !== "all" ? <input type="hidden" name="view" value={view} /> : null}
            <label className="sr-only" htmlFor="application-search">
              Search applications
            </label>
            <input
              id="application-search"
              name="q"
              defaultValue={params.q ?? ""}
              placeholder="Search applications"
              className={inputClass}
            />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              ...VIEWS.map((item) => ({
                label: item.label,
                href: hrefFor(item.id, q),
                active: view === item.id,
              })),
              { label: "Waiting list", href: "/dashboard/waiting-list" },
            ]}
          />
        </div>
        {page.items.length === 0 ? (
          <EmptyState
            title="No applications"
            description={view === "all" && !q ? "Create a housing application to begin." : "Nothing matches this view."}
            action={
              view === "all" && !q
                ? { label: "New application", href: "/dashboard/housing-applications/new" }
                : { label: "Show all", href: "/dashboard/housing-applications" }
            }
          />
        ) : (
          <DataTable caption="Housing applications">
            <thead>
              <tr>
                <Th>Application</Th>
                <Th>Need</Th>
                <Th>Submitted</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50">
                  <Td>
                    <div className="flex items-center gap-3">
                      <Avatar name={row.reference_number} size="sm" />
                      <div>
                        <Link
                          href={`/dashboard/housing-applications/${row.id}`}
                          className="font-semibold text-slate-900 hover:text-brand-700 hover:underline"
                        >
                          {row.reference_number}
                        </Link>
                        <p className="text-xs text-slate-500">{humanize(row.accommodation_type || row.priority)}</p>
                      </div>
                    </div>
                  </Td>
                  <Td className="max-w-xs truncate">{row.housing_requirements || "—"}</Td>
                  <Td className="whitespace-nowrap">{shortDate(row.submitted_at)}</Td>
                  <Td>
                    <StatusChip status={row.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <p className="text-xs text-slate-500">
          Showing {from}–{to} of {page.total}
        </p>
      </div>
    );
  } catch {
    return (
      <ErrorState
        title="Couldn't load applications"
        description="Something went wrong on our side. Please try again."
        retryHref="/dashboard/housing-applications"
      />
    );
  }
}
