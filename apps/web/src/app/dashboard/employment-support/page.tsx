import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchEmploymentSummary, fetchJobMatchProgress } from "@/lib/employmentApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { StaffNotesForm } from "./StaffNotesForm";

export default async function EmploymentSupportPage({
  searchParams,
}: {
  searchParams?: Promise<{ tenantId?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/employment-support");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "employment.prep.read.assigned",
      "employment_support.manage.assigned",
      "tenants.manage",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load employment support." />;
  }
  const params = searchParams ? await searchParams : {};
  const tenantId = params.tenantId?.trim();
  if (!tenantId) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow="F5.3"
          title="Employment support"
          description="Authorised staff can view a limited skills and employment preparation summary for an assigned tenant. Full CVs and application notes stay private unless policy grants access."
        />
        <EmptyState
          title="Tenant ID required"
          description="Open this page with ?tenantId=<uuid> for an authorised tenant in your organisation."
        />
      </div>
    );
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const summary = await fetchEmploymentSummary({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      tenantId,
    });
    const matchProgress = await fetchJobMatchProgress({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      tenantId,
    });
    const canWriteNotes = canAny(session.authorization?.permissions, [
      "employment_support.manage.assigned",
      "tenants.manage",
      "employment.prep.read.assigned",
    ]);
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow="F5.3 / F5.4"
          title="Employment support summary"
          description="Self-reported skills are not formally verified qualifications. CV PDFs and private applications stay restricted. Match scores are advisory only."
        />
        <dl className="grid gap-4 rounded-lg border border-slate-200 bg-white p-5 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Assessment</dt>
            <dd className="mt-1 text-sm">
              {summary.assessment_status ?? "Not started"} · {summary.completion_percent ?? 0}%
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">CVs</dt>
            <dd className="mt-1 text-sm">{summary.cv_count}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Applications</dt>
            <dd className="mt-1 text-sm">{summary.application_count}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase text-slate-500">Open goals</dt>
            <dd className="mt-1 text-sm">{summary.open_goals}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold uppercase text-slate-500">Skill names</dt>
            <dd className="mt-1 text-sm">
              {summary.skill_names.length ? summary.skill_names.join(", ") : "None recorded"}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold uppercase text-slate-500">Career goals</dt>
            <dd className="mt-1 text-sm">
              {summary.career_goals?.length ? summary.career_goals.join(", ") : "None recorded"}
            </dd>
          </div>
          {matchProgress ? (
            <>
              <div>
                <dt className="text-xs font-semibold uppercase text-slate-500">Saved matched jobs</dt>
                <dd className="mt-1 text-sm">{matchProgress.saved_jobs}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-slate-500">Match history</dt>
                <dd className="mt-1 text-sm">{matchProgress.match_count}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-semibold uppercase text-slate-500">Top match scores</dt>
                <dd className="mt-1 text-sm">
                  {matchProgress.top_scores.length
                    ? matchProgress.top_scores.join(", ")
                    : "None yet"}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-semibold uppercase text-slate-500">Preferred categories</dt>
                <dd className="mt-1 text-sm">
                  {matchProgress.preferred_categories.length
                    ? matchProgress.preferred_categories.join(", ")
                    : "None recorded"}
                </dd>
              </div>
            </>
          ) : null}
        </dl>
        {canWriteNotes ? (
          <StaffNotesForm
            tenantId={tenantId}
            organisationId={orgId}
            role={session.authorization?.active_role}
            accessToken={token}
            initialNotes={summary.staff_support_notes ?? ""}
          />
        ) : null}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load summary."} />
    );
  }
}
