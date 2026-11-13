import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { getVoiceDashboard, listVoiceCalls } from "@/lib/voiceCallingApi";

const READ = ["voice_calling.read", "voice_calling.manage"];

export default async function VoiceCallingPage() {
  const session = await requireAuthenticatedSession("/dashboard/voice-calling");
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
  let calls: Record<string, unknown>[] = [];
  try {
    stats = await getVoiceDashboard(token, orgId);
    calls = await listVoiceCalls(token, orgId);
  } catch {
    return (
      <ErrorState description="Voice calling add-on is disabled or unavailable. Enable VOICE_CALLING_GLOBAL_ENABLED and organisation settings when approved." />
    );
  }
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">AI voice calling (add-on)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Mock telephony only until provider credentials are approved. Calls are not recorded by default.
        </p>
      </header>
      <section className="grid gap-4 sm:grid-cols-3">
        <Stat label="Total calls" value={String(stats.total_calls ?? "0")} />
        <Stat label="Failed" value={String(stats.failed_calls ?? "0")} />
        <Stat label="Handovers" value={String(stats.handover_calls ?? "0")} />
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="font-medium text-slate-800">Recent calls</h2>
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {calls.length === 0 ? (
            <li className="py-2 text-slate-500">No call sessions yet.</li>
          ) : (
            calls.slice(0, 20).map((c) => (
              <li key={String(c.id)} className="flex justify-between py-2">
                <span>{String(c.direction)} — {String(c.status)}</span>
                <span className="text-slate-500">{String(c.started_at ?? "")}</span>
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
