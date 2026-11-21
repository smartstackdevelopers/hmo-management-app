/**
 * Server-side session and authorization helpers.
 * Active role and permissions always come from the API (or Auth0 session absence),
 * never from client-supplied role storage.
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { DEMO_LOGIN_COOKIE, isWebDemoAuthEnabled } from "@/lib/demoAuth";
import { isNativeAuthEnabled, readNativeAccessToken } from "@/lib/nativeAuth";
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
  /** API error body or hint when authorization snapshot fails. */
  authorizationDetail: string | null;
};

async function loadAuthorization(
  token: string,
): Promise<{
  authorization: AuthorizationSnapshot | null;
  authorizationError: DashboardSession["authorizationError"];
  authorizationDetail: string | null;
}> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/rbac/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (response.status === 401) {
      return {
        authorization: null,
        authorizationError: "unauthenticated",
        authorizationDetail: "API rejected the access token.",
      };
    }
    if (response.status === 403) {
      return {
        authorization: null,
        authorizationError: "forbidden",
        authorizationDetail: "No active HMore role membership for this account.",
      };
    }
    if (!response.ok) {
      const body = await response.text().catch(() => "");
      return {
        authorization: null,
        authorizationError: "api_unreachable",
        authorizationDetail: body ? body.slice(0, 200) : `HTTP ${response.status}`,
      };
    }
    return {
      authorization: (await response.json()) as AuthorizationSnapshot,
      authorizationError: "none",
      authorizationDetail: null,
    };
  } catch (err) {
    return {
      authorization: null,
      authorizationError: "api_unreachable",
      authorizationDetail:
        err instanceof Error
          ? err.message
          : "Could not reach the API at " + API_BASE,
    };
  }
}

export async function getDashboardSession(): Promise<DashboardSession> {
  if (isWebDemoAuthEnabled()) {
    const jar = await cookies();
    const demoToken = jar.get(DEMO_LOGIN_COOKIE)?.value;
    if (demoToken) {
      const loaded = await loadAuthorization(demoToken);
      const role = loaded.authorization?.active_role ?? "demo";
      return {
        authConfigured: true,
        authenticated: true,
        user: {
          sub: `demo|${role}`,
          email: `demo-${role}@hmore.local`,
          name: `Demo ${String(role).replaceAll("_", " ")}`,
        },
        ...loaded,
      };
    }
  }

  if (isNativeAuthEnabled()) {
    const token = await readNativeAccessToken();
    if (!token) {
      return {
        authConfigured: true,
        authenticated: false,
        user: null,
        authorization: null,
        authorizationError: "unauthenticated",
        authorizationDetail: null,
      };
    }
    const loaded = await loadAuthorization(token);
    return {
      authConfigured: true,
      authenticated: true,
      user: {
        sub: loaded.authorization?.user_id ?? "native",
        email: null,
        name: "HMore user",
      },
      ...loaded,
    };
  }

  if (!isAuth0Configured() || !auth0) {
    return {
      authConfigured: isWebDemoAuthEnabled(),
      authenticated: false,
      user: null,
      authorization: null,
      authorizationError: isWebDemoAuthEnabled() ? "unauthenticated" : "none",
      authorizationDetail: null,
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
      authorizationDetail: null,
    };
  }

  let token: string | undefined;
  try {
    token = (await auth0.getAccessToken())?.token;
  } catch {
    token = undefined;
  }

  if (!token) {
    return {
      authConfigured: true,
      authenticated: true,
      user: {
        sub: session.user.sub,
        email: session.user.email,
        name: session.user.name ?? session.user.nickname,
      },
      authorization: null,
      authorizationError: "unauthenticated",
      authorizationDetail: "No access token available.",
    };
  }

  const loaded = await loadAuthorization(token);
  return {
    authConfigured: true,
    authenticated: true,
    user: {
      sub: session.user.sub,
      email: session.user.email,
      name: session.user.name ?? session.user.nickname,
    },
    ...loaded,
  };
}

export async function requireAuthenticatedSession(
  returnTo: string,
): Promise<DashboardSession> {
  const snapshot = await getDashboardSession();
  if (!snapshot.authConfigured && !isWebDemoAuthEnabled()) {
    return snapshot;
  }
  if (!snapshot.authenticated) {
    if (isNativeAuthEnabled()) {
      redirect(`${LOGIN_PATH}?returnTo=${encodeURIComponent(returnTo)}`);
    }
    if (isWebDemoAuthEnabled()) {
      redirect(`/demo-login?returnTo=${encodeURIComponent(returnTo)}`);
    }
    redirect(`${LOGIN_PATH}?returnTo=${encodeURIComponent(returnTo)}`);
  }
  return snapshot;
}

export async function requireDashboardRole(
  required: F19DashboardRole,
  returnTo: string,
): Promise<DashboardSession> {
  const snapshot = await requireAuthenticatedSession(returnTo);
  if (!snapshot.authConfigured && !isWebDemoAuthEnabled()) {
    return snapshot;
  }
  if (snapshot.authorizationError === "forbidden") {
    redirect(UNAUTHORIZED_PATH);
  }
  const activeRole = snapshot.authorization?.active_role ?? null;
  if (!snapshot.authorization) {
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
