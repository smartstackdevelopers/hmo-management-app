import { redirect } from "next/navigation";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export async function requireReportAccess(path: string, permissions: string[]) {
  const session = await requireAuthenticatedSession(path);
  if (session.authorization && !canAny(session.authorization.permissions, [...permissions, "reports.read"])) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId || !isAuth0Configured() || !auth0) {
    return { session, token: null as string | null, orgId: null as string | null };
  }
  const token = (await auth0.getAccessToken())?.token ?? null;
  return { session, token, orgId };
}
