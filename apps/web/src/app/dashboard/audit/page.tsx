import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Avatar, DataTable, StatusChip, Td, Th, btnSecondary, humanize, inputClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listAuditEvents } from "@/lib/orgWorkflowsApi";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const UK_TIME_ZONE = "Europe/London";

function whenLabel(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
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

export default async function DashboardAuditPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/audit");
  if (session.authorization && !can(session.authorization.permissions, "audit_logs.read")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see the audit log." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so the audit log can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/audit" />;
  }

  const params = searchParams ? await searchParams : {};
  const query = (params.q ?? "").trim().toLowerCase();
  let items: Array<Record<string, unknown>> = [];
  let total = 0;
  try {
    const res = await listAuditEvents({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    items = res.items;
    total = res.total;
  } catch {
    return (
      <ErrorState
        title="Couldn't load the audit log"
        description="Something went wrong on our side. Please try again."
        retryHref="/dashboard/audit"
      />
    );
  }

  const visible = query
    ? items.filter((event) =>
        `${event.action ?? ""} ${event.resource_type ?? ""} ${event.summary ?? ""} ${event.actor_role ?? ""} ${event.outcome ?? ""}`
          .toLowerCase()
          .includes(query),
      )
    : items;
  const from = visible.length === 0 ? 0 : 1;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Platform"
        title="Audit logs"
        description="Every sensitive action, who did it and when."
      />
      <form method="get" className="flex max-w-xl items-center gap-2">
        <label className="sr-only" htmlFor="audit-search">
          Search actor, action or record
        </label>
        <input
          id="audit-search"
          name="q"
          defaultValue={params.q ?? ""}
          placeholder="Search actor, action or record"
          className={inputClass}
        />
        <button type="submit" className={btnSecondary}>
          Search
        </button>
      </form>
      {visible.length === 0 ? (
        <EmptyState
          title={query ? "No matching events" : "No events"}
          description={query ? "Nothing on this page of the log matches that search." : "Sensitive actions will be listed here."}
          action={query ? { label: "Clear search", href: "/dashboard/audit" } : undefined}
        />
      ) : (
        <DataTable caption="Organisation audit events">
          <thead>
            <tr>
              <Th>Actor</Th>
              <Th>Action</Th>
              <Th>Record</Th>
              <Th>When</Th>
              <Th>Result</Th>
            </tr>
          </thead>
          <tbody>
            {visible.map((event) => {
              const actor = event.actor_role ? humanize(String(event.actor_role)) : "Unknown";
              return (
                <tr key={String(event.id)}>
                  <Td>
                    <span className="flex items-center gap-3">
                      <Avatar name={actor} size="sm" />
                      <span className="font-semibold text-slate-900">{actor}</span>
                    </span>
                  </Td>
                  <Td>{humanize(String(event.action ?? ""))}</Td>
                  <Td>{event.summary ? String(event.summary) : humanize(String(event.resource_type ?? ""))}</Td>
                  <Td className="whitespace-nowrap text-slate-500">{whenLabel(event.created_at)}</Td>
                  <Td>
                    <StatusChip status={String(event.outcome ?? "")} />
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {from}–{visible.length} of {query ? visible.length : total}
      </p>
    </div>
  );
}
