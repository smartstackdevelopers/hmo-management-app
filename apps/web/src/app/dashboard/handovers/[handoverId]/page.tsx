import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader, StatusChip } from "@/components/ui/primitives";
import { HandoverActions } from "@/components/support/HandoverActions";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default async function HandoverDetailPage({
  params,
}: {
  params: Promise<{ handoverId: string }>;
}) {
  const { handoverId } = await params;
  const session = await requireAuthenticatedSession(`/dashboard/handovers/${handoverId}`);
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, ["support_notes.read.assigned", "tenants.read"])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  const userId = session.authorization?.user_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load handover." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }

  try {
    const response = await fetch(`${API_BASE}/api/v1/handovers/${handoverId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Organisation-Id": orgId,
        ...(session.authorization?.active_role
          ? { "X-HMore-Role": session.authorization.active_role }
          : {}),
      },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const handover = (await response.json()) as {
      id: string;
      summary: string;
      status: string;
      priority: string;
      case_updates?: string | null;
      outstanding_tasks?: string | null;
      follow_up_actions?: string | null;
      created_by_user_id: string;
      recipient_user_id: string;
      handover_at: string;
      tenant_id: string;
    };

    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow="My work"
          title={handover.summary}
          actions={
            <div className="flex flex-wrap gap-2">
              <StatusChip status={handover.status} />
              <StatusChip status={handover.priority} />
            </div>
          }
        />
        <Card>
          <CardHeader title="When" description={new Date(handover.handover_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })} />
        </Card>
        <Card>
          <div className="space-y-4 text-sm">
            <div>
              <h2 className="font-semibold text-slate-900">Case updates</h2>
              <p className="mt-1 whitespace-pre-wrap text-slate-700">{handover.case_updates || "—"}</p>
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">Outstanding tasks</h2>
              <p className="mt-1 whitespace-pre-wrap text-slate-700">{handover.outstanding_tasks || "—"}</p>
            </div>
            <div>
              <h2 className="font-semibold text-slate-900">Follow-up actions</h2>
              <p className="mt-1 whitespace-pre-wrap text-slate-700">{handover.follow_up_actions || "—"}</p>
            </div>
          </div>
        </Card>
        <HandoverActions
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          handoverId={handover.id}
          status={handover.status}
          isRecipient={userId === handover.recipient_user_id}
          isCreator={userId === handover.created_by_user_id}
        />
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load handover."} />
    );
  }
}
