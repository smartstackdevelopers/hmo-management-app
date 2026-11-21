/**
 * Native HMore web authentication (Prompt 12).
 * HttpOnly cookies store access + refresh tokens issued by FastAPI.
 */

import { cookies } from "next/headers";

export const NATIVE_ACCESS_COOKIE = "hmore_access_token";
export const NATIVE_REFRESH_COOKIE = "hmore_refresh_token";

export function isNativeAuthEnabled(): boolean {
  // Stakeholder default: native auth on. Set NEXT_PUBLIC_NATIVE_AUTH=0 only for emergency Auth0 experiments.
  return process.env.NEXT_PUBLIC_NATIVE_AUTH !== "0";
}

export async function readNativeAccessToken(): Promise<string | null> {
  const jar = await cookies();
  return jar.get(NATIVE_ACCESS_COOKIE)?.value?.trim() || null;
}

export async function readNativeRefreshToken(): Promise<string | null> {
  const jar = await cookies();
  return jar.get(NATIVE_REFRESH_COOKIE)?.value?.trim() || null;
}

export function cookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: maxAgeSeconds,
  };
}
