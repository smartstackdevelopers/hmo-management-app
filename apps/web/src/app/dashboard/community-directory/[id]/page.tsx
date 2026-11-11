import Link from "next/link";
import { redirect } from "next/navigation";
import { CommunityServiceActions } from "@/components/community/CommunityServiceActions";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  getAdminCommunityService,
  listVerificationHistory,
} from "@/lib/communityDirectoryApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm text-forest-900">{value?.trim() ? value : "Not provided"}</dd>
    </div>
  );
}

export default async function CommunityServiceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/community-directory");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "organisations.manage",
      "organisation.settings.manage",
    ]) &&
    session.authorization.active_role !== "organisation_admin" &&
    session.authorization.active_role !== "super_admin"
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load listing." />;
  }
  const { id } = await params;
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const [service, history] = await Promise.all([
      getAdminCommunityService({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization?.active_role,
        serviceId: id,
      }),
      listVerificationHistory({
        accessToken: token,
        organisationId: orgId,
        role: session.authorization?.active_role,
        serviceId: id,
      }),
    ]);
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <PageHeader
          eyebrow="F5.1"
          title={service.name}
          description={`${service.category.replaceAll("_", " ")} · ${service.verification_status.replaceAll("_", " ")}`}
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link href="/dashboard/community-directory" className="rounded-md border border-slate-300 px-3 py-2">
            Back to directory
          </Link>
          <Link
            href={`/dashboard/community-directory/${service.id}/edit`}
            className="rounded-md bg-teal-700 px-3 py-2 text-white"
          >
            Edit listing
          </Link>
        </div>
        <dl className="grid gap-4 rounded-lg border border-slate-200 bg-white p-5 sm:grid-cols-2">
          <Field label="Description" value={service.description} />
          <Field label="Address" value={service.address_line} />
          <Field label="Opening days" value={service.opening_days} />
          <Field label="Opening hours" value={service.opening_hours} />
          <Field label="Eligibility" value={service.eligibility} />
          <Field label="Referral requirements" value={service.referral_requirements} />
          <Field label="Contact" value={service.contact} />
          <Field label="Instructions" value={service.service_instructions} />
          <Field label="Clothing service type" value={service.clothing_service_type} />
          <Field label="Information source" value={service.information_source} />
          <Field
            label="Last verified"
            value={service.verified_at ? new Date(service.verified_at).toLocaleString() : null}
          />
          <Field
            label="Updated"
            value={service.updated_at ? new Date(service.updated_at).toLocaleString() : null}
          />
          <Field label="Published" value={service.is_published ? "Yes" : "No"} />
          <Field label="Internal verification notes" value={service.verification_notes} />
        </dl>
        <CommunityServiceActions
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          serviceId={service.id}
          status={service.verification_status}
        />
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold text-forest-900">Verification history</h2>
          {history.items.length === 0 ? (
            <p className="text-sm text-slate-600">No history events yet.</p>
          ) : (
            <ul className="space-y-3 text-sm">
              {history.items.map((event) => (
                <li key={event.id} className="border-b border-slate-100 pb-2 last:border-0">
                  <p className="font-medium text-forest-900">
                    {event.action.replaceAll("_", " ")} → {event.to_status.replaceAll("_", " ")}
                  </p>
                  <p className="text-slate-600">
                    {new Date(event.created_at).toLocaleString()}
                    {event.notes ? ` · ${event.notes}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load listing."} />
    );
  }
}
