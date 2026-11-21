import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { can } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { redirect } from "next/navigation";

export default async function DashboardFilesPage() {
  const session = await requireAuthenticatedSession("/dashboard/files");
  const permissions = session.authorization?.permissions;
  if (session.authorization && !can(permissions, "files.read")) {
    redirect("/unauthorized");
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow="Files"
        title="Private files"
        description="Files stay in private storage. Nothing on this page is published to a public link."
      />
      <EmptyState
        title="No files to show"
        description="When a file is uploaded for this organisation, it will be listed here."
      />
    </div>
  );
}
