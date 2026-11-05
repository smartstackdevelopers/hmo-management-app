import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { requireDashboardRole } from "@/lib/session";

export default async function SuperAdminOrganisationsPage() {
  await requireDashboardRole("super_admin", "/dashboard/super-admin/organisations");

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow="Platform"
        title="Organisations"
        description="Organisation create/list UIs bind to existing FastAPI organisation endpoints. No client-side organisation inventing."
      />
      <EmptyState
        title="Organisation list not loaded in F1.9"
        description="Use POST /api/v1/organisations (Super Admin) when the API is running. A full admin directory UI is a later enhancement."
        hint="Navigation entry is provided so the shell has a clear platform destination."
      />
    </div>
  );
}
