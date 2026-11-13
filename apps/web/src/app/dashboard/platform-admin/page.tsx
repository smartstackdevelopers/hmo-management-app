import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function PlatformAdminPage() {
  const session = await requireAuthenticatedSession("/dashboard/platform-admin");
  if (session.authorization?.active_role !== "super_admin") {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Unavailable" description="Organisation header required for API calls even for Super Admin." />;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold text-slate-900">Platform administration (F8.12)</h1>
      <p className="text-sm text-slate-600">
        Super Admin platform dashboard data is served from <code className="text-xs">/api/v1/platform-governance/platform/dashboard</code>.
        Use API clients or extend this page with authenticated fetches; figures are database-backed only.
      </p>
      <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
        <li>Organisation approvals and suspension</li>
        <li>Platform branding (non-secret)</li>
        <li>Security alert sync from audit events</li>
        <li>Integration hub webhook failure counts</li>
      </ul>
      <Link href="/dashboard/governance" className="inline-block text-sm text-blue-700 hover:underline">
        Organisation governance hub
      </Link>
    </div>
  );
}
