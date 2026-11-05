/**
 * Auth0 Authorization Code + PKCE foundation for Expo (F1.3).
 *
 * This module does not replace the legacy Room Ready local JWT AuthContext.
 * Wire screens to these helpers after a UK/EU Auth0 Native application is configured.
 */
import * as AuthSession from "expo-auth-session";
import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";

WebBrowser.maybeCompleteAuthSession();

const ACCESS_TOKEN_KEY = "hmore.auth0.accessToken";
const REFRESH_TOKEN_KEY = "hmore.auth0.refreshToken";
const ID_TOKEN_KEY = "hmore.auth0.idToken";
const EXPIRES_AT_KEY = "hmore.auth0.expiresAt";

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

export async function getStoredAccessToken(): Promise<string | null> {
  const expiresAtRaw = await SecureStore.getItemAsync(EXPIRES_AT_KEY);
  if (expiresAtRaw) {
    const expiresAt = Number(expiresAtRaw);
    if (Number.isFinite(expiresAt) && Date.now() >= expiresAt - 30_000) {
      await clearAuth0Tokens();
      return null;
    }
  }
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
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
