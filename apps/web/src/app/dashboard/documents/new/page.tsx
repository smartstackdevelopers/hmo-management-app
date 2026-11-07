import { redirect } from "next/navigation";
import { DocumentUploadForm } from "@/components/documents/DocumentUploadForm";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { listDocumentCategories, seedDocumentCategories } from "@/lib/managedDocumentsApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DocumentUploadPage() {
  const session = await requireAuthenticatedSession("/dashboard/documents/new");
  if (session.authorization && !canAny(session.authorization.permissions, ["documents.upload"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Select or join an organisation with an active membership." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Configure Auth0 for the web app." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;

  try {
    await seedDocumentCategories({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
  } catch {
    /* categories may already exist */
  }

  let categories: Array<{ id: string; code: string; title: string }>;
  try {
    categories = await listDocumentCategories({
      accessToken: token,
      organisationId: orgId,
      role: session.authorization?.active_role,
    });
  } catch (e) {
    return <ErrorState description={e instanceof Error ? e.message : "Failed to load categories"} />;
  }

  if (categories.length === 0) {
    return <EmptyState title="No categories" description="An organisation admin must create document categories first." />;
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader title="Upload document" description="Files go to private storage via the API; the browser never sees bucket URLs." />
      <DocumentUploadForm
        accessToken={token}
        organisationId={orgId}
        role={session.authorization?.active_role}
        categories={categories}
      />
    </div>
  );
}
