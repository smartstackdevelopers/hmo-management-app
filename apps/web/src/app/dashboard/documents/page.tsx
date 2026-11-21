import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import {
  Avatar,
  DataTable,
  FilterTabs,
  StatCard,
  StatGrid,
  StatusChip,
  Td,
  Th,
  btnPrimary,
  btnSecondary,
  humanize,
  inputClass,
} from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchDocumentsDashboard, listDocuments } from "@/lib/managedDocumentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const UK_TIME_ZONE = "Europe/London";

function shortDate(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: UK_TIME_ZONE }).format(date);
}

function linkedLabel(row: Record<string, unknown>): string {
  if (!Array.isArray(row.links)) return "—";
  const label = row.links
    .map((link) => (link && typeof link === "object" && "label" in link ? String((link as { label?: string }).label ?? "") : ""))
    .find((item) => item.trim().length > 0);
  return label || "—";
}

function countOf(dashboard: Record<string, unknown> | null, key: string): number | "—" {
  return typeof dashboard?.[key] === "number" ? (dashboard[key] as number) : "—";
}

export default async function DocumentsDashboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ q?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/documents");
  if (session.authorization && !canAny(session.authorization.permissions, ["documents.read.meta"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see documents." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so documents can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/documents" />;
  }

  const params = searchParams ? await searchParams : {};
  const q = params.q?.trim() || undefined;
  const role = session.authorization?.active_role;
  let dashboard: Record<string, unknown> | null = null;
  let items: Record<string, unknown>[] = [];
  let total = 0;
  try {
    dashboard = await fetchDocumentsDashboard({ accessToken: token, organisationId: orgId, role });
    const list = await listDocuments({ accessToken: token, organisationId: orgId, role, page: 1, pageSize: 20, q });
    items = list.items as Record<string, unknown>[];
    total = list.total;
  } catch {
    return (
      <ErrorState
        title="Couldn't load documents"
        description="Something went wrong on our side. Your files are safe — please try again."
        retryHref="/dashboard/documents"
      />
    );
  }

  const from = items.length === 0 ? 0 : 1;
  const to = items.length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Documents"
        title="Documents"
        description="Certificates, tenancy files and signatures."
        actions={
          <>
            <Link className={btnPrimary} href="/dashboard/documents/new">
              + Upload
            </Link>
            <Link className={btnSecondary} href="/dashboard/documents/retention">
              Retention
            </Link>
          </>
        }
      />
      <StatGrid>
        <StatCard label="Expiring soon" value={countOf(dashboard, "expiring_soon")} tone="amber" href="/dashboard/documents/expiring" />
        <StatCard label="Expired" value={countOf(dashboard, "expired")} tone="red" href="/dashboard/documents/expired" />
        <StatCard label="Awaiting signature" value={countOf(dashboard, "pending_signatures")} tone="amber" href="/dashboard/documents/signatures" />
        <StatCard label="Total" value={countOf(dashboard, "total_documents")} />
      </StatGrid>
      <div className="flex flex-wrap items-center gap-3">
        <form method="get" className="flex min-w-[16rem] flex-1 items-center gap-2">
          <label className="sr-only" htmlFor="document-search">
            Search documents
          </label>
          <input id="document-search" name="q" defaultValue={params.q ?? ""} placeholder="Search documents" className={inputClass} />
          <button type="submit" className={btnSecondary}>
            Search
          </button>
        </form>
        <FilterTabs
          tabs={[
            { label: "All", href: "/dashboard/documents", active: true },
            { label: "Expiring", href: "/dashboard/documents/expiring" },
            { label: "Expired", href: "/dashboard/documents/expired" },
            { label: "Signatures", href: "/dashboard/documents/signatures" },
          ]}
        />
      </div>
      {items.length === 0 ? (
        <EmptyState
          title={q ? "No matching documents" : "No documents yet"}
          description={q ? "Try a different title or reference." : "Upload a certificate or tenancy file to see it here."}
          action={q ? { label: "Clear search", href: "/dashboard/documents" } : { label: "Upload", href: "/dashboard/documents/new" }}
        />
      ) : (
        <DataTable caption="Documents">
          <thead>
            <tr>
              <Th>Document</Th>
              <Th>Linked to</Th>
              <Th>Type</Th>
              <Th>Expires</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={String(row.id)} className="hover:bg-slate-50">
                <Td>
                  <div className="flex items-center gap-3">
                    <Avatar name={String(row.title || "Document")} size="sm" />
                    <Link href={`/dashboard/documents/${row.id}`} className="font-semibold text-slate-900 hover:text-brand-700 hover:underline">
                      {String(row.title || "Untitled")}
                    </Link>
                  </div>
                </Td>
                <Td>{linkedLabel(row)}</Td>
                <Td>{row.category_code ? humanize(String(row.category_code)) : "—"}</Td>
                <Td className="whitespace-nowrap">{shortDate(row.expiry_date)}</Td>
                <Td>
                  <StatusChip status={String(row.status || row.expiry_tracking || "")} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {from}–{to} of {total}
      </p>
    </div>
  );
}
