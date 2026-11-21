import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardHeader } from "@/components/ui/primitives";
import { DailyLogForm } from "@/components/support/DailyLogForm";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function NewDailyLogPage({
  searchParams,
}: {
  searchParams?: Promise<{ tenantId?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/daily-logs/new");
  const params = searchParams ? await searchParams : {};
  if (session.authorization && !can(session.authorization.permissions, "support_notes.create.assigned")) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot create daily logs." />;
  }
  const tokenResult = await auth0.getAccessToken();
  const token = tokenResult?.token;
  if (!token) {
    return <ErrorState description="Access token unavailable." />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Records"
        title="New daily log"
        description="Record facts clearly. Tenants may request to see their records."
      />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <DailyLogForm
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          defaultTenantId={params.tenantId}
        />
        <Card>
          <CardHeader title="Guidance" />
          <ul className="space-y-3 text-sm text-slate-600">
            <li className="flex gap-2">
              <span aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-600" />
              Write facts, not opinions.
            </li>
            <li className="flex gap-2">
              <span aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-600" />
              Mark safeguarding concerns as an incident, not a log.
            </li>
            <li className="flex gap-2">
              <span aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-600" />
              Note bodies are stored on the case, not in audit metadata.
            </li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
