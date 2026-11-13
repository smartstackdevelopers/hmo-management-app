import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { getRentPaymentsDashboard, listRentObligations } from "@/lib/rentPaymentsApi";

const READ = ["rent_payments.read", "rent_payments.manage", "rent_payments.read.own"];

export default async function RentPaymentsPage() {
  const session = await requireAuthenticatedSession("/dashboard/rent-payments");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  let stats: Record<string, unknown> = {};
  let obligations: Record<string, unknown>[] = [];
  try {
    stats = await getRentPaymentsDashboard(token, orgId);
    obligations = await listRentObligations(token, orgId);
  } catch {
    return (
      <ErrorState description="Rent payments add-on is disabled until RENT_PAYMENTS_GLOBAL_ENABLED and organisation settings are approved." />
    );
  }
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Rent & tenancy payments (add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Extends the F6.1 rent ledger. Manual payments require verification; gateway runs in test mode unless approved.
        </p>
      </header>
      <section className="grid gap-4 sm:grid-cols-3">
        <Stat label="Total due" value={String(stats.total_rent_due ?? "0")} />
        <Stat label="Received (verified)" value={String(stats.total_rent_received ?? "0")} />
        <Stat label="Outstanding" value={String(stats.outstanding_rent ?? "0")} />
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="font-medium text-slate-800">Obligations</h2>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {obligations.length === 0 ? (
            <li className="py-2 text-slate-500">No rent obligations synced.</li>
          ) : (
            obligations.slice(0, 25).map((o) => (
              <li key={String(o.rent_record_id)} className="flex justify-between py-2">
                <span>
                  {String(o.payment_status)} — {String(o.outstanding_balance)} {String(o.currency)}
                </span>
                <span className="text-slate-500">Due {String(o.due_date ?? "—")}</span>
              </li>
            ))
          )}
        </ul>
      </section>
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
