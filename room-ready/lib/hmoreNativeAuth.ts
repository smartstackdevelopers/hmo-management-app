import { resolveHmoreApiBase } from '@/lib/hmore/config';
import { clearAuth0Tokens, storeAuth0Tokens } from '@/lib/hmoreAuth0';
import { getSecureStorage } from '@/lib/secureStorage';

const NATIVE_SESSION_KEY = 'hmore.auth.nativeSession';

export function isNativeAuthEnabled(): boolean {
  // Default on for Prompt 12. Set EXPO_PUBLIC_NATIVE_AUTH=0 to force demo/Auth0 experiments.
  return process.env.EXPO_PUBLIC_NATIVE_AUTH !== '0';
}

export async function markNativeSessionActive(): Promise<void> {
  await getSecureStorage().setItem(NATIVE_SESSION_KEY, '1');
}

export async function clearNativeSessionFlag(): Promise<void> {
  await getSecureStorage().deleteItem(NATIVE_SESSION_KEY);
}

export async function isNativeSessionActive(): Promise<boolean> {
  if (!isNativeAuthEnabled()) return false;
  const flag = await getSecureStorage().getItem(NATIVE_SESSION_KEY);
  return flag === '1';
}

export async function loginWithPassword(email: string, password: string): Promise<{
  accessToken: string;
  email: string;
}> {
  const base = resolveHmoreApiBase().replace(/\/$/, '');
  let response: Response;
  try {
    response = await fetch(`${base}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error(`Could not reach HMore at ${base}. Check the API is running.`);
  }
  if (!response.ok) {
    throw new Error(await readApiError(response, `Login failed (${response.status})`));
  }
  const payload = (await response.json()) as {
    access_token: string;
    refresh_token?: string;
    expires_in?: number;
    user?: { email?: string };
  };
  await clearAuth0Tokens();
  await storeAuth0Tokens({
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    expiresAt: payload.expires_in ? Date.now() + payload.expires_in * 1000 : undefined,
  });
  await markNativeSessionActive();
  return { accessToken: payload.access_token, email: payload.user?.email || email };
}

/** Rotate native refresh token via FastAPI (never Auth0). */
export async function refreshNativeAccessToken(refreshToken: string): Promise<string | null> {
  const base = resolveHmoreApiBase().replace(/\/$/, '');
  let response: Response;
  try {
    response = await fetch(`${base}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    return null;
  }
  if (!response.ok) {
    return null;
  }
  const payload = (await response.json().catch(() => null)) as {
    access_token?: string;
    refresh_token?: string;
    expires_in?: number;
  } | null;
  if (!payload?.access_token) return null;
  await storeAuth0Tokens({
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token ?? refreshToken,
    expiresAt: payload.expires_in ? Date.now() + payload.expires_in * 1000 : undefined,
  });
  await markNativeSessionActive();
  return payload.access_token;
}

export async function registerWithPassword(input: {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
  requestedRole: string;
  phone?: string;
  organisationSlug?: string;
  invitationCode?: string;
  termsAccepted: boolean;
  privacyAccepted: boolean;
}): Promise<void> {
  const base = resolveHmoreApiBase().replace(/\/$/, '');
  let response: Response;
  try {
    response = await fetch(`${base}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        full_name: input.fullName,
        email: input.email,
        password: input.password,
        confirm_password: input.confirmPassword,
        requested_role: input.requestedRole,
        phone: input.phone || null,
        organisation_slug: input.organisationSlug || null,
        invitation_code: input.invitationCode || null,
        terms_accepted: input.termsAccepted,
        privacy_accepted: input.privacyAccepted,
      }),
    });
  } catch {
    throw new Error(`Could not reach HMore at ${base}. Check the API is running.`);
  }
  if (!response.ok) {
    throw new Error(await readApiError(response, `Registration failed (${response.status})`));
  }
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  const raw = await response.text().catch(() => '');
  if (!raw) return fallback;
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: unknown }).msg);
          }
          return '';
        })
        .filter(Boolean);
      if (parts.length) return parts.join('; ');
    }
  } catch {
    // keep raw text
  }
  return raw.length > 280 ? `${raw.slice(0, 280)}…` : raw;
}
