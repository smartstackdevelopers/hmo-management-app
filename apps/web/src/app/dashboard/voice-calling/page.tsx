import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, StatCard, StatGrid, StatusChip, Td, Th } from "@/components/ui/primitives";
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
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  let stats: Record<string, unknown> = {};
  let calls: Record<string, unknown>[] = [];
  try {
    stats = await getVoiceDashboard(token, orgId);
    calls = await listVoiceCalls(token, orgId);
  } catch {
    return (
      <ErrorState
        title="Voice calling unavailable"
        description="Voice calling isn't switched on for this organisation yet."
        retryHref="/dashboard/voice-calling"
      />
    );
  }
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="AI"
        title="Voice calling"
        description="Calls stay off until a provider is approved. Calls are not recorded by default."
      />
      <StatGrid>
        <StatCard label="Total calls" value={String(stats.total_calls ?? "0")} />
        <StatCard label="Failed" value={String(stats.failed_calls ?? "0")} tone="red" />
        <StatCard label="Handovers" value={String(stats.handover_calls ?? "0")} tone="amber" />
      </StatGrid>
      {calls.length === 0 ? (
        <EmptyState title="No call sessions yet" description="Sessions appear here after voice calling is enabled for this organisation." />
      ) : (
        <DataTable caption="Recent voice calls">
          <thead>
            <tr>
              <Th>Direction</Th>
              <Th>Status</Th>
              <Th>Started</Th>
            </tr>
          </thead>
          <tbody>
            {calls.slice(0, 20).map((c) => (
              <tr key={String(c.id)}>
                <Td className="font-semibold text-slate-900">{String(c.direction)}</Td>
                <Td>
                  <StatusChip status={String(c.status)} />
                </Td>
                <Td className="whitespace-nowrap text-slate-500">{String(c.started_at ?? "—")}</Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {calls.length === 0 ? "0" : `1–${Math.min(20, calls.length)}`} of {calls.length}
      </p>
    </div>
  );
}
