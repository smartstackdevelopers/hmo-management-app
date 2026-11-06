import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 for the web app." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
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
  } catch (e) {
    err = e instanceof Error ? e.message : "Failed";
  }
  if (err) {
    return <ErrorState description={err} />;
  }

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="F2.12" title="Delivery status" description="Queued vs provider_accepted vs delivered vs failed" />
      {items.length === 0 ? (
        <p className="text-slate-600">No delivery rows visible.</p>
      ) : (
        <ul className="divide-y rounded border border-slate-200 bg-white text-sm">
          {items.map((d) => (
            <li key={String(d.id)} className="flex flex-wrap gap-2 px-4 py-2">
              <span className="font-mono text-xs text-slate-500">{String(d.id).slice(0, 8)}…</span>
              <span>{String(d.channel)}</span>
              <span className="rounded bg-slate-100 px-2 py-0.5">{String(d.status)}</span>
              {d.last_error ? <span className="text-red-700">{String(d.last_error)}</span> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
