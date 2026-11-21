import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, btnSecondary, DataTable, FilterTabs, humanize, inputClass, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchTraining } from "@/lib/complianceApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function trainingHref(next: { view?: string; status?: string; q?: string }) {
  const search = new URLSearchParams();
  if (next.view && next.view !== "all") search.set("view", next.view);
  if (next.status) search.set("status", next.status);
  if (next.q) search.set("q", next.q);
  const query = search.toString();
  return query ? `/dashboard/training?${query}` : "/dashboard/training";
}

export default async function TrainingPage({
  searchParams,
}: {
  searchParams?: Promise<{ view?: string; status?: string; q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/training");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "training.records.manage",
      "training.records.read.own",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see training." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in isn't set up yet" description="Training records will be available once sign-in is configured." />;
  }
  const params = searchParams ? await searchParams : {};
  const view = params.view === "expiring" || params.view === "expired" ? params.view : "all";
  const q = (params.q ?? "").trim();
  const canCreate = Boolean(session.authorization?.permissions?.includes("training.records.manage"));
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/training" />;
    const page = await fetchTraining({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      expiringOnly: view === "expiring",
      expiredOnly: view === "expired",
    });
    const statuses = [...new Set(page.items.map((row) => row.effective_status).filter(Boolean))].sort();
    const status = statuses.includes(params.status ?? "") ? params.status ?? "" : "";
    const needle = q.toLowerCase();
    const visible = page.items.filter((row) => {
      if (status && row.effective_status !== status) return false;
      if (!needle) return true;
      return row.title.toLowerCase().includes(needle) || row.category.toLowerCase().includes(needle) || row.staff_user_id.toLowerCase().includes(needle);
    });
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Me"
          title="Staff training"
          description="Training records and expiry dates set by your organisation."
          actions={
            canCreate ? (
              <Link href="/dashboard/training/new" className={btnPrimary}>
                + New record
              </Link>
            ) : null
          }
        />
        <div className="flex flex-wrap items-center gap-3">
          <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
            {view !== "all" ? <input type="hidden" name="view" value={view} /> : null}
            {status ? <input type="hidden" name="status" value={status} /> : null}
            <label className="sr-only" htmlFor="training-search">
              Search training
            </label>
            <input id="training-search" name="q" defaultValue={q} placeholder="Search title or staff reference" className={inputClass} />
            <button type="submit" className={btnSecondary}>
              Search
            </button>
          </form>
          <FilterTabs
            tabs={[
              { label: "All", href: trainingHref({ q }), active: view === "all" && !status },
              { label: "Expiring soon", href: trainingHref({ view: "expiring", q }), active: view === "expiring" && !status },
              { label: "Expired", href: trainingHref({ view: "expired", q }), active: view === "expired" && !status },
              ...statuses.map((item) => ({
                label: humanize(item),
                href: trainingHref({ view, q, status: item }),
                active: status === item,
              })),
              { label: "Safeguarding", href: "/dashboard/safeguarding" },
            ]}
          />
        </div>
        {visible.length === 0 ? (
          <EmptyState
            title="No training records"
            description={q || status || view !== "all" ? "Nothing matches this view." : "Add a record when someone completes training."}
            action={q || status || view !== "all" ? { label: "Show all", href: "/dashboard/training" } : undefined}
          />
        ) : (
          <DataTable caption="Training records">
            <thead>
              <tr>
                <Th>Record</Th>
                <Th>Staff</Th>
                <Th>Completed</Th>
                <Th>Expires</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/60">
                  <Td>
                    <p className="font-semibold text-slate-900">{row.title}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{row.category}</p>
                  </Td>
                  <Td className="font-mono text-xs text-slate-600">{row.staff_user_id.length > 10 ? `…${row.staff_user_id.slice(-6)}` : row.staff_user_id}</Td>
                  <Td>{row.completion_date ?? "—"}</Td>
                  <Td>{row.expiry_date ?? "—"}</Td>
                  <Td>
                    <StatusChip status={row.effective_status} />
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
      <ErrorState description={error instanceof Error ? error.message : "We couldn't load training. Please try again."} retryHref="/dashboard/training" />
    );
  }
}
