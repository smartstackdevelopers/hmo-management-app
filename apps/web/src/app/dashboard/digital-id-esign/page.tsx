import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
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
  if (!token) return <ErrorState description="Access token unavailable." />;

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
      <ErrorState description="Digital ID / e-sign add-on is disabled until DIGITAL_ID_ESIGN_GLOBAL_ENABLED and organisation settings are approved." />
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Digital ID &amp; e-signatures (add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Identity is verified only after authorised review. Signatures record consent — advanced trust services require
          separate provider and legal approval.
        </p>
      </header>
      {admin ? (
        <section className="grid gap-4 sm:grid-cols-4">
          <Stat label="Identity records" value={String(stats.identity_records ?? "0")} />
          <Stat label="Verified identities" value={String(stats.identity_verified ?? "0")} />
          <Stat label="Pending signing" value={String(stats.signing_pending ?? "0")} />
          <Stat label="Completed signing" value={String(stats.signing_completed ?? "0")} />
        </section>
      ) : null}
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="font-medium text-slate-800">My pending signatures</h2>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {pending.length === 0 ? (
            <li className="py-2 text-slate-500">Nothing awaiting your signature.</li>
          ) : (
            pending.map((p) => (
              <li key={String(p.signer_id)} className="flex justify-between py-2">
                <span>{String(p.title)}</span>
                <span className="text-slate-500">{String(p.reference)}</span>
              </li>
            ))
          )}
        </ul>
      </section>
      {admin ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="font-medium text-slate-800">Signing requests</h2>
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {requests.length === 0 ? (
              <li className="py-2 text-slate-500">No requests yet.</li>
            ) : (
              requests.map((r) => (
                <li key={String(r.id)} className="flex justify-between py-2">
                  <span>{String(r.title)}</span>
                  <span className="text-slate-500">{String(r.status)}</span>
                </li>
              ))
            )}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}
