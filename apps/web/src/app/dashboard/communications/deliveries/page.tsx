import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listDeliveries } from "@/lib/communicationsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DeliveriesPage() {
  const session = await requireAuthenticatedSession("/dashboard/communications/deliveries");
  if (!session.authorization || !canAny(session.authorization.permissions, ["communication.deliveries.read"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  }
  let items: Array<Record<string, unknown>> = [];
  let err: string | null = null;
  try {
    const data = await listDeliveries({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization.active_role,
    });
    items = data.items;
  } catch {
    err = "We could not load this page. Please try again.";
  }
  if (err) {
    return <ErrorState description={err} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Communications"
        title="Delivery status"
        description="Queued, provider accepted, delivered, and failed. Provider acceptance does not prove the message reached a device."
      />
      {items.length === 0 ? (
        <EmptyState title="No deliveries" description="No delivery rows are visible." />
      ) : (
        <DataTable caption="Delivery status">
          <thead>
            <tr>
              <Th>Channel</Th>
              <Th>Status</Th>
              <Th>Detail</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((d) => (
              <tr key={String(d.id)} className="hover:bg-slate-50">
                <Td className="font-semibold text-slate-900">{String(d.channel || "—")}</Td>
                <Td>
                  <StatusChip status={String(d.status)} />
                </Td>
                <Td>{d.last_error ? "The last attempt did not go through." : "—"}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
    </div>
  );
}
