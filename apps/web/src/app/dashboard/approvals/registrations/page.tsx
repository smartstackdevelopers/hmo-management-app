import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { requireAuthenticatedSession } from "@/lib/session";
import {
  Avatar,
  DataTable,
  FilterTabs,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
  btnDanger,
  btnPrimary,
  btnSecondary,
  humanize,
  inputClass,
} from "@/components/ui/primitives";
import { approveRegistrationAction, rejectRegistrationAction } from "./actions";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const UK_TIME_ZONE = "Europe/London";

type RegistrationItem = {
  id: string;
  display_name: string | null;
  email: string | null;
  requested_role: string;
  organisation_id: string | null;
  status: string;
  created_at: string | null;
};

function shortWhen(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: UK_TIME_ZONE,
  }).format(date);
}

function hrefFor(status: string, q?: string) {
  const search = new URLSearchParams();
  if (status && status !== "all") search.set("status", status);
  if (q) search.set("q", q);
  const query = search.toString();
  return query ? `/dashboard/approvals/registrations?${query}` : "/dashboard/approvals/registrations";
}

export default async function RegistrationApprovalsPage({
  searchParams,
}: {
  searchParams?: Promise<{ status?: string; q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/approvals/registrations");
  const role = session.authorization?.active_role;
  if (role !== "super_admin" && role !== "organisation_admin") {
    redirect("/unauthorized");
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so registration requests can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/approvals/registrations" />;
  }
  const response = await fetch(`${API_BASE}/api/v1/auth/registration-requests`, {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    return (
      <ErrorState
        title="Couldn't load registration requests"
        description="Something went wrong on our side. Please try again."
        retryHref="/dashboard/approvals/registrations"
      />
    );
  }
  const payload = (await response.json()) as { items: RegistrationItem[] };
  const items = payload.items;
  const params = searchParams ? await searchParams : {};
  const status = params.status === "pending" || params.status === "approved" || params.status === "rejected" ? params.status : "all";
  const query = (params.q ?? "").trim().toLowerCase();
  const pending = items.filter((item) => item.status === "pending");
  const approved = items.filter((item) => item.status === "approved");
  const rejected = items.filter((item) => item.status === "rejected");
  const visible = items.filter((item) => {
    const matchesStatus = status === "all" || item.status === status;
    const haystack = `${item.display_name ?? ""} ${item.email ?? ""} ${item.requested_role}`.toLowerCase();
    return matchesStatus && (!query || haystack.includes(query));
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Platform"
        title="Registration approvals"
        description="Review every new account before it can sign in."
      />
      <StatGrid>
        <StatCard label="Pending" value={pending.length} tone="amber" hint={pending.length > 0 ? "Review" : undefined} />
        <StatCard label="Approved" value={approved.length} tone="green" />
        <StatCard label="Rejected" value={rejected.length} tone="red" />
      </StatGrid>
      <div className="flex flex-wrap items-center gap-3">
        <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
          {status !== "all" ? <input type="hidden" name="status" value={status} /> : null}
          <label className="sr-only" htmlFor="registration-search">
            Search name or email
          </label>
          <input
            id="registration-search"
            name="q"
            defaultValue={params.q ?? ""}
            placeholder="Search name or email"
            className={inputClass}
          />
          <button type="submit" className={btnSecondary}>
            Search
          </button>
        </form>
        <FilterTabs
          tabs={[
            { label: "All", href: hrefFor("all", query || undefined), active: status === "all" },
            { label: "Pending", href: hrefFor("pending", query || undefined), active: status === "pending" },
            { label: "Approved", href: hrefFor("approved", query || undefined), active: status === "approved" },
            { label: "Rejected", href: hrefFor("rejected", query || undefined), active: status === "rejected" },
          ]}
        />
      </div>
      {visible.length === 0 ? (
        <EmptyState
          title="No registration requests"
          description={status === "all" && !query ? "New account requests will appear here for review." : "Nothing matches this view."}
          action={status !== "all" || query ? { label: "Show all", href: "/dashboard/approvals/registrations" } : undefined}
        />
      ) : (
        <DataTable caption="Registration requests">
          <thead>
            <tr>
              <Th>Applicant</Th>
              <Th>Email</Th>
              <Th>Requested role</Th>
              <Th>Requested</Th>
              <Th>Status</Th>
              <Th>Decision</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((item) => (
              <tr key={item.id}>
                <Td>
                  <span className="flex items-center gap-3">
                    <Avatar name={item.display_name || item.email || "Applicant"} size="sm" />
                    <span className="font-semibold text-slate-900">{item.display_name || "Applicant"}</span>
                  </span>
                </Td>
                <Td>{item.email || "—"}</Td>
                <Td>{humanize(item.requested_role)}</Td>
                <Td className="whitespace-nowrap text-slate-500">{shortWhen(item.created_at)}</Td>
                <Td>
                  <StatusChip status={item.status} />
                </Td>
                <Td>
                  {item.status === "pending" ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <form action={approveRegistrationAction}>
                        <input type="hidden" name="request_id" value={item.id} />
                        <button type="submit" className={btnPrimary}>
                          Approve
                        </button>
                      </form>
                      <form action={rejectRegistrationAction} className="flex flex-wrap items-center gap-2">
                        <input type="hidden" name="request_id" value={item.id} />
                        <label className="sr-only" htmlFor={`reject-${item.id}`}>
                          Reason for rejecting {item.display_name || item.email || "this applicant"}
                        </label>
                        <input
                          id={`reject-${item.id}`}
                          name="rejection_reason"
                          placeholder="Reason"
                          className={`${inputClass} w-44`}
                          required
                        />
                        <button type="submit" className={btnDanger}>
                          Reject
                        </button>
                      </form>
                    </div>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {visible.length === 0 ? "0" : `1–${visible.length}`} of {items.length}
      </p>
    </div>
  );
}
