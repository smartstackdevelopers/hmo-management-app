import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { TenantTimelinePanel } from "@/components/tenant/TenantTimelinePanel";
import { fetchCaseDetail } from "@/lib/supportApi";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function CaseDetailPage({
  params,
}: {
  params: Promise<{ tenantId: string }>;
}) {
  const { tenantId } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/caseload/${tenantId}`);
  const permissions = session.authorization?.permissions;
  if (
    session.authorization &&
    !canAny(permissions, ["support_notes.read.assigned", "tenants.manage", "tenants.read"])
  ) {
    redirect("/unauthorized");
  }

  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }

  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load case detail." />;
  }

  try {
    const tokenResult = await auth0.getAccessToken();
    const token = tokenResult?.token;
    if (!token) {
      return <ErrorState description="Access token unavailable." />;
    }
    const detail = await fetchCaseDetail({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      tenantId,
    });
    const canReadTimeline = Boolean(
      permissions &&
        canAny(permissions, [
          "timeline.read",
          "timeline.read.own",
          "timeline.read.landlord",
        ]),
    );

    const tenant = detail.tenant as {
      preferred_name?: string;
      full_name?: string;
      tenancy_reference?: string;
      email?: string;
      phone?: string;
      status?: string;
    };

    return (
      <div className="mx-auto max-w-4xl space-y-8">
        <PageHeader
          eyebrow="Case"
          title={tenant.preferred_name || tenant.full_name || "Tenant case"}
          description="Support notes and handovers for this assigned case. Sensitive content is API-gated."
        />

        <dl className="grid gap-3 rounded-lg border border-slate-200 bg-white p-5 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Tenancy reference</dt>
            <dd className="font-medium text-forest-900">{tenant.tenancy_reference || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Status</dt>
            <dd className="font-medium text-forest-900">{tenant.status || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Email</dt>
            <dd className="font-medium text-forest-900">{tenant.email || "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Phone</dt>
            <dd className="font-medium text-forest-900">{tenant.phone || "—"}</dd>
          </div>
        </dl>

        <div className="flex flex-wrap gap-3">
          <Link
            href={`/dashboard/daily-logs/new?tenantId=${tenantId}`}
            className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white"
          >
            Add daily log
          </Link>
          <Link
            href={`/dashboard/handovers/new?tenantId=${tenantId}`}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            Create handover
          </Link>
          <Link href="/dashboard/support-worker" className="rounded-md px-3 py-2 text-sm text-teal-800 underline">
            Back to caseload
          </Link>
        </div>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-forest-900">Recent daily logs</h2>
          {detail.recent_logs.length === 0 ? (
            <p className="text-sm text-slate-600">No logs yet.</p>
          ) : (
            <ul className="space-y-3">
              {detail.recent_logs.map((log) => (
                <li key={log.id} className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="font-medium text-forest-900">{log.summary}</p>
                  <p className="text-xs text-slate-500">
                    {log.log_date} · {log.activity_category} · {log.status}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{log.notes}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-forest-900">Tenant timeline</h2>
          <p className="text-sm text-slate-600">
            Aggregated view of permitted activity. Each item links to an underlying record — access is enforced on the
            detail APIs.
          </p>
          <TenantTimelinePanel
            accessToken={token}
            organisationId={orgId}
            role={session.authorization?.active_role}
            tenantId={tenantId}
            canReadTimeline={canReadTimeline}
          />
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-forest-900">Recent handovers</h2>
          {detail.recent_handovers.length === 0 ? (
            <p className="text-sm text-slate-600">No handovers yet.</p>
          ) : (
            <ul className="space-y-3">
              {detail.recent_handovers.map((item) => (
                <li key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="font-medium text-forest-900">{item.summary}</p>
                  <p className="text-xs text-slate-500">
                    {item.status} · {item.priority} · {new Date(item.handover_at).toLocaleString()}
                  </p>
                  <Link
                    href={`/dashboard/handovers/${item.id}`}
                    className="mt-2 inline-block text-sm text-teal-800 underline"
                  >
                    View handover
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState
        description={error instanceof Error ? error.message : "Unable to load case detail."}
      />
    );
  }
}
