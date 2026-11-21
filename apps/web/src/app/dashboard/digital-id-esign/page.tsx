import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { CardHeader, DataTable, StatCard, StatGrid, StatusChip, Td, Th } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import {
  getDigitalIdEsignDashboard,
  listMyPendingSignatures,
  listSigningDashboard,
} from "@/lib/digitalIdEsignApi";

const READ = [
  "digital_id_esign.read",
  "digital_id_esign.manage",
  "digital_id_esign.sign",
  "digital_id_esign.sign.request",
];

export default async function DigitalIdEsignPage() {
  const session = await requireAuthenticatedSession("/dashboard/digital-id-esign");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;

  const perms = session.authorization?.permissions ?? [];
  const admin = perms.includes("digital_id_esign.manage") || perms.includes("digital_id_esign.reports");

  let stats: Record<string, unknown> = {};
  let requests: Record<string, unknown>[] = [];
  let pending: Record<string, unknown>[] = [];

  try {
    if (admin) {
      stats = await getDigitalIdEsignDashboard(token, orgId);
      requests = await listSigningDashboard(token, orgId);
    }
    pending = await listMyPendingSignatures(token, orgId);
  } catch {
    return (
      <ErrorState
        title="Signing unavailable"
        description="Digital signing isn't switched on for this organisation yet."
        retryHref="/dashboard/digital-id-esign"
      />
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Compliance / Signatures"
        title="Digital ID and e-signatures"
        description="Identity is verified only after authorised review. Signatures record consent — advanced trust services require separate provider and legal approval."
      />
      {admin ? (
        <StatGrid>
          <StatCard label="Identity records" value={String(stats.identity_records ?? "0")} />
          <StatCard label="Verified identities" value={String(stats.identity_verified ?? "0")} tone="green" />
          <StatCard
            label="Pending signing"
            value={String(stats.signing_pending ?? "0")}
            tone="amber"
            hint={Number(stats.signing_pending ?? 0) > 0 ? "Pending" : undefined}
          />
          <StatCard label="Completed signing" value={String(stats.signing_completed ?? "0")} />
        </StatGrid>
      ) : null}
      <div className="space-y-3">
        <CardHeader title="My pending signatures" description="Requests waiting for your acknowledgement." />
        {pending.length === 0 ? (
          <EmptyState title="Nothing to sign" description="Nothing is awaiting your signature." />
        ) : (
          <DataTable caption="Pending signatures">
            <thead>
              <tr>
                <Th>Title</Th>
                <Th>Reference</Th>
              </tr>
            </thead>
            <tbody>
              {pending.map((p) => (
                <tr key={String(p.signer_id)} className="hover:bg-slate-50">
                  <Td className="font-semibold text-slate-900">{String(p.title)}</Td>
                  <Td className="text-slate-500">{String(p.reference)}</Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </div>
      {admin ? (
        <div className="space-y-3">
          <CardHeader title="Signing requests" />
          {requests.length === 0 ? (
            <EmptyState title="No requests" description="No signing requests have been created yet." />
          ) : (
            <DataTable caption="Signing requests">
              <thead>
                <tr>
                  <Th>Title</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {requests.map((r) => (
                  <tr key={String(r.id)} className="hover:bg-slate-50">
                    <Td className="font-semibold text-slate-900">{String(r.title)}</Td>
                    <Td>
                      <StatusChip status={String(r.status)} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
          )}
        </div>
      ) : null}
    </div>
  );
}
