/**
 * Server-side session and authorization helpers.
 * Active role and permissions always come from the API (or Auth0 session absence),
 * never from client-supplied role storage.
 */

import { redirect } from "next/navigation";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  LOGIN_PATH,
  UNAUTHORIZED_PATH,
  type AuthorizationSnapshot,
} from "@/lib/rbac";
import {
  canAccessRoleHome,
  homePathForRole,
  type F19DashboardRole,
} from "@/lib/dashboardAccess";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type DashboardSession = {
  authConfigured: boolean;
  authenticated: boolean;
  user: {
    sub?: string;
    email?: string | null;
    name?: string | null;
  } | null;
  authorization: AuthorizationSnapshot | null;
  authorizationError: "none" | "api_unreachable" | "forbidden" | "unauthenticated";
};

export async function getDashboardSession(): Promise<DashboardSession> {
  if (!isAuth0Configured() || !auth0) {
    return {
      authConfigured: false,
      authenticated: false,
      user: null,
      authorization: null,
      authorizationError: "none",
    };
  }

  const session = await auth0.getSession();
  if (!session) {
    return {
      authConfigured: true,
      authenticated: false,
      user: null,
      authorization: null,
      authorizationError: "unauthenticated",
    };
  }

  let authorization: AuthorizationSnapshot | null = null;
  let authorizationError: DashboardSession["authorizationError"] = "none";

  try {
    const tokenResult = await auth0.getAccessToken();
    const token = tokenResult?.token;
    if (!token) {
      authorizationError = "unauthenticated";
    } else {
      const response = await fetch(`${API_BASE}/api/v1/rbac/me`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (response.status === 401) {
        authorizationError = "unauthenticated";
      } else if (response.status === 403) {
        authorizationError = "forbidden";
      } else if (!response.ok) {
        authorizationError = "api_unreachable";
      } else {
        authorization = (await response.json()) as AuthorizationSnapshot;
      }
    }
  } catch {
    authorizationError = "api_unreachable";
  }

  return {
    authConfigured: true,
    authenticated: true,
    user: {
      sub: session.user.sub,
      email: session.user.email,
      name: session.user.name ?? session.user.nickname,
    },
    authorization,
    authorizationError,
  };
}

export async function requireAuthenticatedSession(
  returnTo: string,
): Promise<DashboardSession> {
  const snapshot = await getDashboardSession();
  if (!snapshot.authConfigured) {
    return snapshot;
  }
  if (!snapshot.authenticated) {
    redirect(`${LOGIN_PATH}?returnTo=${encodeURIComponent(returnTo)}`);
  }
  return snapshot;
}

export async function requireDashboardRole(
  required: F19DashboardRole,
  returnTo: string,
): Promise<DashboardSession> {
  const snapshot = await requireAuthenticatedSession(returnTo);
  if (!snapshot.authConfigured) {
    return snapshot;
  }
  if (snapshot.authorizationError === "forbidden") {
    redirect(UNAUTHORIZED_PATH);
  }
  const activeRole = snapshot.authorization?.active_role ?? null;
  if (!snapshot.authorization) {
    // Authenticated with Auth0 but no HMore membership / API down — stay on page
    // with empty states rather than inventing a role.
    return snapshot;
  }
  if (!canAccessRoleHome(activeRole, required)) {
    redirect(UNAUTHORIZED_PATH);
  }
  return snapshot;
}

export function redirectToRoleHome(activeRole: string | null | undefined): never {
  redirect(homePathForRole(activeRole));
}
