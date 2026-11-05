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
        title="Private files"
        description="F1.8 private storage. Uploads go through the authenticated API — never directly to a public bucket."
      />
      <EmptyState
        title="File library UI not expanded in F1.9"
        description="Use the PrivateFileUpload component or POST /api/v1/files with a bearer token and organisation context."
      />
    </div>
  );
}
