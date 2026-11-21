import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th, btnSecondary } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchWaitingList } from "@/lib/housingApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function WaitingListPage() {
  const session = await requireAuthenticatedSession("/dashboard/waiting-list");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["waiting_list.manage", "waiting_list.read"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
    const page = await fetchWaitingList({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          eyebrow="Housing / Waiting list"
          title="Housing waiting list"
          description="Organisation FIFO positions with optional priority labels. Position does not guarantee allocation."
          actions={
            <Link href="/dashboard/housing-applications" className={btnSecondary}>
              Applications
            </Link>
          }
        />
        {page.items.length === 0 ? (
          <EmptyState
            title="Waiting list empty"
            description="Approved applications can be added from the application detail page."
            action={{ label: "Applications", href: "/dashboard/housing-applications" }}
          />
        ) : (
          <DataTable caption="Housing waiting list">
            <thead>
              <tr>
                <Th>Position</Th>
                <Th>Application</Th>
                <Th>Priority</Th>
                <Th>List status</Th>
                <Th>Application status</Th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50">
                  <Td className="font-semibold text-slate-900">#{row.position}</Td>
                  <Td>
                    <Link
                      href={`/dashboard/housing-applications/${row.application_id}`}
                      className="font-semibold text-slate-900 hover:text-brand-700 hover:underline"
                    >
                      {row.application_reference || "Open application"}
                    </Link>
                  </Td>
                  <Td>
                    <StatusChip status={row.priority} />
                  </Td>
                  <Td>
                    <StatusChip status={row.status} />
                  </Td>
                  <Td>
                    <StatusChip status={row.application_status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
        <p className="text-xs text-slate-500">
          Showing {page.items.length === 0 ? "0" : `1–${page.items.length}`} of {page.total}
        </p>
      </div>
    );
  } catch {
    return (
      <ErrorState
        title="Couldn't load the waiting list"
        description="Something went wrong on our side. Please try again."
        retryHref="/dashboard/waiting-list"
      />
    );
  }
}
