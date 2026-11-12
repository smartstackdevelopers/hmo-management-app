import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { RoomOccupancyDashboard } from "@/components/occupancy/RoomOccupancyDashboard";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

const READ = ["occupancy.read", "occupancy.alerts.manage", "occupancy.settings.manage"];

export default async function RoomOccupancyPage() {
  const session = await requireAuthenticatedSession("/dashboard/room-occupancy");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return <EmptyState title="Unavailable" description="Organisation context required." />;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="Access token unavailable." />;
  const perms = session.authorization?.permissions ?? [];
  return (
    <RoomOccupancyDashboard
      accessToken={token}
      organisationId={orgId}
      role={session.authorization?.active_role}
      canManage={canAny(perms, ["occupancy.settings.manage"])}
      canCorrect={canAny(perms, ["occupancy.counts.correct"])}
    />
  );
}
