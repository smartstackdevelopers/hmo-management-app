/**
 * Auth token source for Next.js server components.
 *
 * Prompt 12: Auth0 is no longer the active application authentication dependency.
 * This module keeps the historical `auth0` / `isAuth0Configured` names so existing
 * dashboard pages continue to call `auth0.getAccessToken()` without a 99-file rewrite.
 * Tokens come from native HttpOnly cookies (or demo cookie via session.ts).
 */

import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { DEMO_LOGIN_COOKIE, isWebDemoAuthEnabled } from "@/lib/demoAuth";
import { isNativeAuthEnabled, readNativeAccessToken } from "@/lib/nativeAuth";

function hasLegacyAuth0Env(): boolean {
  return Boolean(
    process.env.AUTH0_DOMAIN &&
      process.env.AUTH0_CLIENT_ID &&
      process.env.AUTH0_CLIENT_SECRET &&
      process.env.AUTH0_SECRET &&
      process.env.APP_BASE_URL &&
      process.env.HMORE_ALLOW_AUTH0 === "true",
  );
}

/** True when the app can obtain a server-side API access token. */
export function isAuth0Configured(): boolean {
  return isNativeAuthEnabled() || isWebDemoAuthEnabled() || hasLegacyAuth0Env();
}

type TokenResult = { token: string };

async function getAccessToken(): Promise<TokenResult | undefined> {
  const token = await readNativeAccessToken();
  if (token) return { token };
  if (isWebDemoAuthEnabled()) {
    const jar = await cookies();
    const demoToken = jar.get(DEMO_LOGIN_COOKIE)?.value;
    if (demoToken) return { token: demoToken };
  }
  return undefined;
}

async function getSession(): Promise<{
  user: { sub?: string; email?: string | null; name?: string | null; nickname?: string | null };
} | null> {
  const token = await readNativeAccessToken();
  if (!token) return null;
  // Lightweight session for UI; RBAC still comes from /rbac/me.
  return {
    user: {
      sub: "native",
      email: null,
      name: "HMore user",
    },
  };
}

async function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const auth0 = isAuth0Configured()
  ? {
      getAccessToken,
      getSession,
      middleware,
    }
  : null;
