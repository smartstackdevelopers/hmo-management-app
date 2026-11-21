import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { NATIVE_ACCESS_COOKIE, NATIVE_REFRESH_COOKIE } from "@/lib/nativeAuth";
import { DEMO_LOGIN_COOKIE } from "@/lib/demoAuth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(request: Request) {
  const jar = await cookies();
  const refresh = jar.get(NATIVE_REFRESH_COOKIE)?.value;
  if (refresh) {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
      cache: "no-store",
    }).catch(() => undefined);
  }
  jar.delete(NATIVE_ACCESS_COOKIE);
  jar.delete(NATIVE_REFRESH_COOKIE);
  jar.delete(DEMO_LOGIN_COOKIE);
  const url = new URL("/login", request.url);
  return NextResponse.redirect(url);
}
