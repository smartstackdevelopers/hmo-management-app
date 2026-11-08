/**
 * Auth0 Authorization Code + PKCE for the Expo tenant app.
 * Tokens stay in SecureStore. Access tokens are refreshed with the refresh-token grant
 * before they expire. Nothing in this module writes tokens to logs.
 */
import * as AuthSession from "expo-auth-session";
import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";

WebBrowser.maybeCompleteAuthSession();

const ACCESS_TOKEN_KEY = "hmore.auth0.accessToken";
const REFRESH_TOKEN_KEY = "hmore.auth0.refreshToken";
const ID_TOKEN_KEY = "hmore.auth0.idToken";
const EXPIRES_AT_KEY = "hmore.auth0.expiresAt";

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

export function createAuth0RedirectUri(scheme = "roomready"): string {
  return AuthSession.makeRedirectUri({ scheme, path: "auth/callback" });
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
  if (result.type !== "success" || !result.params.code) {
    throw new Error("Auth0 login was cancelled or failed");
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
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, tokens.accessToken);
  if (tokens.idToken) {
    await SecureStore.setItemAsync(ID_TOKEN_KEY, tokens.idToken);
  }
  if (tokens.refreshToken) {
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, tokens.refreshToken);
  }
  if (tokens.expiresAt) {
    await SecureStore.setItemAsync(EXPIRES_AT_KEY, String(tokens.expiresAt));
  }
}

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAuth0AccessToken(): Promise<string | null> {
  const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  const config = readAuth0ConfigFromEnv();
  if (!refreshToken || !config?.domain || !config.clientId) {
    await clearAuth0Tokens();
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
    await clearAuth0Tokens();
    return null;
  }

  const payload = (await response.json().catch(() => null)) as {
    access_token?: string;
    id_token?: string;
    refresh_token?: string;
    expires_in?: number;
  } | null;

  if (!payload?.access_token) {
    await clearAuth0Tokens();
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
  const accessToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
  if (!accessToken) return null;

  const expiresAtRaw = await SecureStore.getItemAsync(EXPIRES_AT_KEY);
  const expiresAt = expiresAtRaw ? Number(expiresAtRaw) : null;
  if (!accessTokenNeedsRefresh(expiresAt)) return accessToken;

  if (!refreshInFlight) {
    refreshInFlight = refreshAuth0AccessToken().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function clearAuth0Tokens(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(ID_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  await SecureStore.deleteItemAsync(EXPIRES_AT_KEY);
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
