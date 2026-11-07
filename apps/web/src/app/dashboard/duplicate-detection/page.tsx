import { redirect } from "next/navigation";
import { DuplicateDetectionPanel } from "@/components/duplicates/DuplicateDetectionPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  canReadDuplicateDetection,
  canRunDuplicateDetection,
} from "@/lib/duplicateDetectionView";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function DuplicateDetectionPage() {
  const session = await requireAuthenticatedSession("/dashboard/duplicate-detection");
  const permissions = session.authorization?.permissions ?? [];
  if (!canRunDuplicateDetection(permissions) && !canReadDuplicateDetection(permissions)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Organisation required" description="Active organisation needed." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return <EmptyState title="Auth0 not configured" description="Cannot load duplicate detection." />;
  }
  try {
    const token = (await auth0.getAccessToken())?.token;
    if (!token) return <ErrorState description="Access token unavailable." />;
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <PageHeader
          title="Duplicate detection"
          description="Search-based potential duplicate finding for human review. No AI call per record. Never auto-merges or deletes."
        />
        <DuplicateDetectionPanel
          accessToken={token}
          organisationId={orgId}
          role={session.authorization?.active_role}
          permissions={permissions}
        />
      </div>
    );
  } catch {
    return <ErrorState description="Unable to load duplicate detection." />;
  }
}
