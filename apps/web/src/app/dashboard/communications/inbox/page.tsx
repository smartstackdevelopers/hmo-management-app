import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Avatar, Card, StatusChip, btnSecondary, humanize, inputClass } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listInbox } from "@/lib/communicationsApi";
import { canAny } from "@/lib/rbac";
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

export default async function InboxPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string; id?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/communications/inbox");
  if (!session.authorization || !canAny(session.authorization.permissions, ["communication.messages.read"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see messages." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so the inbox can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/communications/inbox" />;
  }

  const params = searchParams ? await searchParams : {};
  const query = (params.q ?? "").trim().toLowerCase();
  let rows: Array<Record<string, unknown>> = [];
  let total = 0;
  try {
    const data = await listInbox({ accessToken: token, organisationId: orgId, role: session.authorization.active_role });
    rows = data.items;
    total = data.total;
  } catch {
    return (
      <ErrorState
        title="Couldn't load messages"
        description="Something went wrong on our side. Your messages are safe — please try again."
        retryHref="/dashboard/communications/inbox"
      />
    );
  }

  const visible = query
    ? rows.filter((row) => `${row.subject ?? ""} ${row.body_preview ?? ""}`.toLowerCase().includes(query))
    : rows;
  const selected =
    visible.find((row) => String(row.message_id) === params.id) ?? visible[0] ?? null;
  const from = visible.length === 0 ? 0 : 1;
  const to = visible.length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Communications"
        title="Inbox"
        description="Messages, announcements and reminders."
        actions={
          <Link href="/dashboard/communications/announcements" className={btnSecondary}>
            Announcement
          </Link>
        }
      />
      <form method="get" className="flex max-w-xl items-center gap-2">
        <label className="sr-only" htmlFor="inbox-search">
          Search messages
        </label>
        <input
          id="inbox-search"
          name="q"
          defaultValue={params.q ?? ""}
          placeholder="Search subject or message"
          className={inputClass}
        />
        <button type="submit" className={btnSecondary}>
          Search
        </button>
      </form>
      {visible.length === 0 ? (
        <EmptyState
          title={query ? "No matching messages" : "Inbox is empty"}
          description={query ? "Nothing in this page of the inbox matches that search." : "New messages will appear here."}
          action={query ? { label: "Clear search", href: "/dashboard/communications/inbox" } : undefined}
        />
      ) : (
        <div className="grid items-start gap-4 lg:grid-cols-[minmax(16rem,20rem)_minmax(0,1fr)_16rem]">
          <Card padded={false} className="overflow-hidden">
            <ul className="divide-y divide-slate-100">
              {visible.map((row) => {
                const id = String(row.message_id);
                const active = selected && String(selected.message_id) === id;
                const unread = !row.read_at;
                const href = `/dashboard/communications/inbox?id=${encodeURIComponent(id)}${params.q ? `&q=${encodeURIComponent(params.q)}` : ""}`;
                return (
                  <li key={String(row.recipient_id ?? id)}>
                    <Link
                      href={href}
                      className={`flex gap-3 px-4 py-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-600 ${active ? "bg-brand-50" : "hover:bg-slate-50"}`}
                    >
                      <Avatar name={String(row.subject || "Message")} size="sm" />
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-semibold text-slate-900">{String(row.subject || "No subject")}</span>
                          {unread ? <span className="h-2 w-2 shrink-0 rounded-full bg-brand-600" aria-label="Unread" /> : null}
                        </span>
                        <span className="mt-0.5 block truncate text-xs text-slate-500">{String(row.body_preview || "")}</span>
                        <span className="mt-1 block text-[11px] text-slate-400">{whenLabel(row.created_at)}</span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </Card>
          <Card>
            {selected ? (
              <div className="space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{String(selected.subject || "No subject")}</h2>
                  <p className="mt-1 text-xs text-slate-500">{whenLabel(selected.created_at)}</p>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">
                  {String(selected.body_preview || "This message has no preview.")}
                </p>
                <StatusChip status={selected.read_at ? "read" : "unread"} tone={selected.read_at ? "gray" : "indigo"}>
                  {selected.read_at ? "Read" : "Unread"}
                </StatusChip>
              </div>
            ) : null}
          </Card>
          <Card>
            <h2 className="text-sm font-semibold text-slate-900">Details</h2>
            {selected ? (
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="text-slate-500">Status</dt>
                  <dd className="mt-0.5 font-medium text-slate-900">{selected.read_at ? "Read" : "Unread"}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Received</dt>
                  <dd className="mt-0.5 font-medium text-slate-900">{whenLabel(selected.created_at)}</dd>
                </div>
                {typeof selected.related_resource_type === "string" && selected.related_resource_type ? (
                  <div>
                    <dt className="text-slate-500">Linked record</dt>
                    <dd className="mt-0.5 font-medium text-slate-900">{humanize(selected.related_resource_type)}</dd>
                  </div>
                ) : null}
              </dl>
            ) : null}
          </Card>
        </div>
      )}
      <p className="text-xs text-slate-500">
        Showing {from}–{to} of {query ? visible.length : total}
      </p>
    </div>
  );
}
