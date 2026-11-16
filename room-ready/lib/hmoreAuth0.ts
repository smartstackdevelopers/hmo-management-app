/**
 * Auth0 Authorization Code + PKCE for the Expo tenant app.
 * Tokens use lib/secureStorage (SecureStore on native, AsyncStorage on web).
 * Access tokens are refreshed with the refresh-token grant before they expire.
 * Nothing in this module writes tokens to logs.
 */
import * as AuthSession from "expo-auth-session";
import * as WebBrowser from "expo-web-browser";
import { getSecureStorage } from "@/lib/secureStorage";

WebBrowser.maybeCompleteAuthSession();

const ACCESS_TOKEN_KEY = "hmore.auth0.accessToken";
const REFRESH_TOKEN_KEY = "hmore.auth0.refreshToken";
const ID_TOKEN_KEY = "hmore.auth0.idToken";
const EXPIRES_AT_KEY = "hmore.auth0.expiresAt";

function tokenStore() {
  return getSecureStorage();
}

/** Refresh shortly before expiry so API calls do not race an expired access token. */
export const ACCESS_TOKEN_REFRESH_SKEW_MS = 60_000;

export function accessTokenNeedsRefresh(
  expiresAt: number | null | undefined,
  now = Date.now(),
): boolean {
  if (expiresAt == null || !Number.isFinite(expiresAt)) return false;
  return now >= expiresAt - ACCESS_TOKEN_REFRESH_SKEW_MS;
}

export type HMoreAuth0Config = {
  domain: string;
  clientId: string;
  audience?: string;
  scheme?: string;
};

export type HMoreAuth0Tokens = {
  accessToken: string;
  idToken?: string;
  refreshToken?: string;
  expiresAt?: number;
};

export function readAuth0ConfigFromEnv(): HMoreAuth0Config | null {
  const domain = process.env.EXPO_PUBLIC_AUTH0_DOMAIN;
  const clientId = process.env.EXPO_PUBLIC_AUTH0_CLIENT_ID;
  if (!domain || !clientId) {
    return null;
  }
  return {
    domain,
    clientId,
    audience: process.env.EXPO_PUBLIC_AUTH0_AUDIENCE,
    scheme: process.env.EXPO_PUBLIC_AUTH0_SCHEME || "roomready",
  };
}

export function isAuth0MobileConfigured(): boolean {
  return readAuth0ConfigFromEnv() !== null;
}

/**
 * Redirect URI Auth0 must allow. Prefer env override for demos;
 * otherwise Expo AuthSession (exp://… on Expo Go, roomready:// on builds, http on web).
 */
export function createAuth0RedirectUri(scheme = "roomready"): string {
  const forced = process.env.EXPO_PUBLIC_AUTH0_REDIRECT_URI?.trim();
  if (forced) {
    return forced;
  }
  return AuthSession.makeRedirectUri({
    scheme,
    path: "auth/callback",
  });
}

/** Call from UI so the operator can paste the URI into Auth0 Allowed Callback URLs. */
export function getAuth0RedirectUriHint(scheme = "roomready"): string {
  return createAuth0RedirectUri(scheme);
}

export function buildAuth0Discovery(domain: string): AuthSession.DiscoveryDocument {
  const base = `https://${domain}`;
  return {
    authorizationEndpoint: `${base}/authorize`,
    tokenEndpoint: `${base}/oauth/token`,
    revocationEndpoint: `${base}/oauth/revoke`,
    endSessionEndpoint: `${base}/v2/logout`,
  };
}

export async function loginWithAuth0(
  config: HMoreAuth0Config = readAuth0ConfigFromEnv()!,
): Promise<HMoreAuth0Tokens> {
  if (!config?.domain || !config.clientId) {
    throw new Error("Auth0 mobile configuration is missing");
  }

  const redirectUri = createAuth0RedirectUri(config.scheme);
  const discovery = buildAuth0Discovery(config.domain);
  const request = new AuthSession.AuthRequest({
    clientId: config.clientId,
    redirectUri,
    scopes: ["openid", "profile", "email", "offline_access"],
    usePKCE: true,
    extraParams: config.audience ? { audience: config.audience } : undefined,
  });

  const result = await request.promptAsync(discovery);
  if (result.type === "cancel" || result.type === "dismiss") {
    throw new Error(
      `Auth0 login was cancelled. If the browser closed by itself, add this callback in Auth0: ${redirectUri}`,
    );
  }
  if (result.type !== "success" || !result.params.code) {
    const detail =
      result.type === "error" && "errorCode" in result
        ? String((result as { errorCode?: string }).errorCode ?? result.type)
        : result.type;
    throw new Error(
      `Auth0 login failed (${detail}). Auth0 → Applications → your Native app → Allowed Callback URLs must include: ${redirectUri}`,
    );
  }

  const tokenResult = await AuthSession.exchangeCodeAsync(
    {
      clientId: config.clientId,
      code: result.params.code,
      redirectUri,
      extraParams: {
        code_verifier: request.codeVerifier || "",
      },
    },
    discovery,
  );

  const tokens: HMoreAuth0Tokens = {
    accessToken: tokenResult.accessToken,
    idToken: tokenResult.idToken,
    refreshToken: tokenResult.refreshToken,
    expiresAt: tokenResult.expiresIn
      ? Date.now() + tokenResult.expiresIn * 1000
      : undefined,
  };
  await storeAuth0Tokens(tokens);
  return tokens;
}

export async function storeAuth0Tokens(tokens: HMoreAuth0Tokens): Promise<void> {
  const store = tokenStore();
  await store.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  if (tokens.idToken) {
    await store.setItem(ID_TOKEN_KEY, tokens.idToken);
  } else {
    await store.deleteItem(ID_TOKEN_KEY);
  }
  if (tokens.refreshToken) {
    await store.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  } else {
    // Demo / access-only login must not keep a stale Auth0 refresh token.
    await store.deleteItem(REFRESH_TOKEN_KEY);
  }
  if (tokens.expiresAt) {
    await store.setItem(EXPIRES_AT_KEY, String(tokens.expiresAt));
  } else {
    await store.deleteItem(EXPIRES_AT_KEY);
  }
}

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAuth0AccessToken(): Promise<string | null> {
  const store = tokenStore();
  const refreshToken = await store.getItem(REFRESH_TOKEN_KEY);
  const config = readAuth0ConfigFromEnv();
  if (!refreshToken || !config?.domain || !config.clientId) {
    return null;
  }

  const body = new URLSearchParams({
    grant_type: "refresh_token",
    client_id: config.clientId,
    refresh_token: refreshToken,
  });

  let response: Response;
  try {
    response = await fetch(`https://${config.domain}/oauth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
  } catch {
    return null;
  }

  if (!response.ok) {
    // Do not wipe local tokens here — the caller may still have a usable access token.
    return null;
  }

  const payload = (await response.json().catch(() => null)) as {
    access_token?: string;
    id_token?: string;
    refresh_token?: string;
    expires_in?: number;
  } | null;

  if (!payload?.access_token) {
    return null;
  }

  const tokens: HMoreAuth0Tokens = {
    accessToken: payload.access_token,
    idToken: payload.id_token,
    refreshToken: payload.refresh_token ?? refreshToken,
    expiresAt: payload.expires_in ? Date.now() + payload.expires_in * 1000 : undefined,
  };
  await storeAuth0Tokens(tokens);
  return tokens.accessToken;
}

export async function getStoredAccessToken(): Promise<string | null> {
  const store = tokenStore();
  const accessToken = await store.getItem(ACCESS_TOKEN_KEY);
  if (!accessToken) return null;

  const expiresAtRaw = await store.getItem(EXPIRES_AT_KEY);
  const expiresAt = expiresAtRaw ? Number(expiresAtRaw) : null;
  if (!accessTokenNeedsRefresh(expiresAt)) return accessToken;

  // Demo / access-only sessions have no refresh token — do not clear the access token.
  const refreshToken = await store.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    return accessToken;
  }

  // When native auth is the active product path, refresh against FastAPI only.
  // Never send a native refresh token to Auth0 — that clears storage and the next
  // API call fails with "Missing Authorization header".
  const { isNativeAuthEnabled, refreshNativeAccessToken, markNativeSessionActive } = await import(
    '@/lib/hmoreNativeAuth'
  );
  if (isNativeAuthEnabled()) {
    if (!refreshInFlight) {
      refreshInFlight = refreshNativeAccessToken(refreshToken)
        .then(async (token) => {
          if (token) {
            await markNativeSessionActive();
            return token;
          }
          // Keep the current access token if refresh is temporarily unavailable.
          return accessToken;
        })
        .finally(() => {
          refreshInFlight = null;
        });
    }
    return refreshInFlight;
  }

  if (!refreshInFlight) {
    refreshInFlight = refreshAuth0AccessToken().finally(() => {
      refreshInFlight = null;
    });
  }
  const refreshed = await refreshInFlight;
  // Keep the existing access token if Auth0 refresh failed (do not drop the header).
  return refreshed ?? accessToken;
}

export async function revokeAuth0RefreshToken(): Promise<void> {
  const refreshToken = await tokenStore().getItem(REFRESH_TOKEN_KEY);
  const config = readAuth0ConfigFromEnv();
  if (!refreshToken || !config?.domain || !config.clientId) return;
  const body = new URLSearchParams({
    client_id: config.clientId,
    token: refreshToken,
    token_type_hint: 'refresh_token',
  });
  try {
    await fetch(`https://${config.domain}/oauth/revoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
  } catch {
    // Local sign-out continues when Auth0 cannot be reached.
  }
}

export async function clearAuth0Tokens(): Promise<void> {
  const store = tokenStore();
  await store.deleteItem(ACCESS_TOKEN_KEY);
  await store.deleteItem(ID_TOKEN_KEY);
  await store.deleteItem(REFRESH_TOKEN_KEY);
  await store.deleteItem(EXPIRES_AT_KEY);
  try {
    const { clearNativeSessionFlag } = await import('@/lib/hmoreNativeAuth');
    await clearNativeSessionFlag();
  } catch {
    // Flag cleanup is best-effort during sign-out.
  }
}

export async function logoutAuth0(
  config: HMoreAuth0Config = readAuth0ConfigFromEnv()!,
): Promise<void> {
  await clearAuth0Tokens();
  if (!config?.domain || !config.clientId) {
    return;
  }
  const returnTo = createAuth0RedirectUri(config.scheme);
  const url =
    `https://${config.domain}/v2/logout` +
    `?client_id=${encodeURIComponent(config.clientId)}` +
    `&returnTo=${encodeURIComponent(returnTo)}`;
  await WebBrowser.openAuthSessionAsync(url, returnTo);
}
