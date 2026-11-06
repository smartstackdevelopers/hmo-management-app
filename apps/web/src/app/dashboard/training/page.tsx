import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { fetchTraining } from "@/lib/complianceApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

function statusClass(status: string): string {
  if (status === "expired") return "text-red-700";
  if (status === "expiring_soon") return "text-amber-700";
  if (status === "completed") return "text-teal-800";
  return "text-slate-700";
}

export default async function TrainingPage({
  searchParams,
}: {
  searchParams?: Promise<{ view?: string }>;
}) {
  const session = await requireAuthenticatedSession("/dashboard/training");
  if (
    session.authorization &&
    !canAny(session.authorization.permissions, [
      "training.records.manage",
      "training.records.read.own",
    ])
  ) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load training." />;
  }
  const params = searchParams ? await searchParams : {};
  const view = params.view ?? "all";
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    const page = await fetchTraining({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
      expiringOnly: view === "expiring",
      expiredOnly: view === "expired",
    });
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          eyebrow="F2.3"
          title="Staff training"
          description="Training records and expiry tracking. Intervals follow organisation policy — not hardcoded statutory rules."
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link href="/dashboard/training/new" className="rounded-md bg-teal-700 px-3 py-2 text-white">
            New record
          </Link>
          <Link href="/dashboard/training" className="rounded-md border border-slate-300 px-3 py-2">
            All
          </Link>
          <Link
            href="/dashboard/training?view=expiring"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Expiring soon
          </Link>
          <Link
            href="/dashboard/training?view=expired"
            className="rounded-md border border-slate-300 px-3 py-2"
          >
            Expired
          </Link>
          <Link href="/dashboard/safeguarding" className="rounded-md border border-slate-300 px-3 py-2">
            Safeguarding
          </Link>
        </div>
        {page.items.length === 0 ? (
          <EmptyState title="No training records" description="Create a record to track compliance." />
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {page.items.map((row) => (
              <li key={row.id} className="p-4 text-sm">
                <p className="font-medium text-forest-900">{row.title}</p>
                <p className={statusClass(row.effective_status)}>
                  {row.effective_status.replaceAll("_", " ")} · {row.category}
                </p>
                <p className="text-slate-600">
                  Completes {row.completion_date ?? "—"} · Expires {row.expiry_date ?? "—"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  } catch (error) {
    return (
      <ErrorState description={error instanceof Error ? error.message : "Failed to load training."} />
    );
  }
}
