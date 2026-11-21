export const DEMO_LOGIN_COOKIE = "hmore_demo_access_token";

export function isWebDemoAuthEnabled(): boolean {
  return process.env.NEXT_PUBLIC_DEMO_AUTH === "1" || process.env.NEXT_PUBLIC_DEMO_AUTH === "true";
}
