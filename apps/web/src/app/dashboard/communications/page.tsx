import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { StatCard, StatGrid } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchCommunicationsDashboard } from "@/lib/communicationsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const ANY_COMM = [
  "communication.messages.read",
  "communication.deliveries.read",
  "communication.reminders.manage",
  "communication.announcements.read",
];

export default async function CommunicationsDashboardPage() {
  const session = await requireAuthenticatedSession("/dashboard/communications");
  if (session.authorization && !canAny(session.authorization.permissions, ANY_COMM)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation membership needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Sign-in not configured" description="Sign-in isn't set up in this environment yet, so this page can't load." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." />;
  }
  const role = session.authorization?.active_role;
  let dashboard: Record<string, unknown> | null = null;
  let err: string | null = null;
  try {
    dashboard = await fetchCommunicationsDashboard({ accessToken: token, organisationId: orgId, role });
  } catch {
    err = "We could not load this page. Please try again.";
  }
  if (err) {
    return <ErrorState description={err} />;
  }
  const n = (k: string) => (typeof dashboard?.[k] === "number" ? (dashboard[k] as number) : "—");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Communications"
        title="Communication dashboard"
        description="Messages, deliveries and reminders for this organisation."
      />

      <StatGrid>
        <StatCard label="Total in-app (inbox)" value={n("total_in_app_messages")} href="/dashboard/communications/inbox" />
        <StatCard label="Unread" value={n("unread_messages")} tone="indigo" href="/dashboard/communications/inbox" />
        <StatCard label="Queued deliveries" value={n("queued_deliveries")} tone="amber" href="/dashboard/communications/deliveries" />
        <StatCard label="Successful deliveries" value={n("successful_deliveries")} tone="green" />
        <StatCard label="Failed deliveries" value={n("failed_deliveries")} tone="red" href="/dashboard/communications/deliveries" />
        <StatCard label="Pending reminders" value={n("pending_reminders")} tone="amber" href="/dashboard/communications/reminders" />
        <StatCard label="Overdue reminders" value={n("overdue_reminders")} tone="red" />
        <StatCard label="Active announcements" value={n("active_emergency_announcements")} href="/dashboard/communications/announcements" />
        <StatCard label="Pending translation reviews" value={n("pending_translation_reviews")} tone="amber" href="/dashboard/communications/translations" />
      </StatGrid>

      <p className="max-w-3xl text-sm leading-6 text-slate-600">
        Delivery status distinguishes queued, provider accepted, delivered (in-app), and failed. Provider acceptance does not prove the message reached the recipient&apos;s device.
      </p>
    </div>
  );
}
