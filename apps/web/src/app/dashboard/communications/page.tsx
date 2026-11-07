import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
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
    return <EmptyState title="Auth0 not configured" description="Cannot load communications." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }
  const role = session.authorization?.active_role;
  let dashboard: Record<string, unknown> | null = null;
  let err: string | null = null;
  try {
    dashboard = await fetchCommunicationsDashboard({ accessToken: token, organisationId: orgId, role });
  } catch (e) {
    err = e instanceof Error ? e.message : "Failed to load";
  }
  if (err) {
    return <ErrorState description={err} />;
  }
  const n = (k: string) => (typeof dashboard?.[k] === "number" ? (dashboard[k] as number) : "—");

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="F2.12"
        title="Communication dashboard"
        description="Counts from GET /api/v1/communications/dashboard. Authorisation is enforced by the API."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(
          [
            ["Total in-app (inbox)", "total_in_app_messages"],
            ["Unread", "unread_messages"],
            ["Queued deliveries", "queued_deliveries"],
            ["Successful deliveries", "successful_deliveries"],
            ["Failed deliveries", "failed_deliveries"],
            ["Pending reminders", "pending_reminders"],
            ["Overdue reminders", "overdue_reminders"],
            ["Active announcements", "active_emergency_announcements"],
            ["Pending translation reviews", "pending_translation_reviews"],
          ] as const
        ).map(([label, key]) => (
          <div key={key} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm text-slate-600">{label}</div>
            <div className="text-2xl font-semibold text-slate-900">{n(key)}</div>
          </div>
        ))}
      </div>

      <p className="text-sm text-slate-600">
        Delivery status distinguishes queued, provider accepted, delivered (in-app), and failed. SMTP/Twilio acceptance does not prove the message reached the recipient&apos;s device. Configure
        providers in the repository file docs/development/ENVIRONMENT_VARIABLES.md (F2.12 section).
      </p>
    </div>
  );
}
