import { resolveHmoreApiBase } from '@/lib/hmore/config';
import { clearAuth0Tokens, storeAuth0Tokens } from '@/lib/hmoreAuth0';
import { setRequestContext } from '@/lib/hmore/requestContext';
import type { AuthMe, RbacMe } from '@/lib/hmore/types';
import type { HmoreSession } from '@/lib/hmore/services/session';

export const DEMO_ROLES = [
  { role: 'super_admin', label: 'Super Admin' },
  { role: 'organisation_admin', label: 'Organisation Admin' },
  { role: 'landlord', label: 'Landlord' },
  { role: 'tenant', label: 'Tenant' },
  { role: 'support_worker', label: 'Support Worker' },
  { role: 'maintenance_contractor', label: 'Maintenance Contractor' },
] as const;

export type DemoRole = (typeof DEMO_ROLES)[number]['role'];

export function isDemoAuthEnabled(): boolean {
  return process.env.EXPO_PUBLIC_DEMO_AUTH === '1' || process.env.EXPO_PUBLIC_DEMO_AUTH === 'true';
}

async function demoFetch<T>(path: string, init: RequestInit): Promise<T> {
  const base = resolveHmoreApiBase().replace(/\/$/, '');
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`;
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new Error(
      `Could not reach HMore at ${base} (${path}). Hard-refresh http://127.0.0.1:8081 and confirm API health at http://127.0.0.1:8000/health.`,
    );
  }
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(detail || `HMore request failed (${response.status}) for ${path}`);
  }
  return (await response.json()) as T;
}

/** Demo login + session load using plain fetch (Metro proxy). Avoids hmore client races. */
export async function loginWithDemoRole(role: DemoRole): Promise<{
  accessToken: string;
  email: string;
  session: HmoreSession;
}> {
  await clearAuth0Tokens();

  const login = await demoFetch<{
    access_token: string;
    email: string;
    expires_in?: number;
  }>('/auth/demo/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ role }),
  });

  await storeAuth0Tokens({
    accessToken: login.access_token,
    expiresAt: login.expires_in ? Date.now() + login.expires_in * 1000 : undefined,
  });

  const authHeaders = {
    Authorization: `Bearer ${login.access_token}`,
    Accept: 'application/json',
  };
  const auth = await demoFetch<AuthMe>('/auth/me', { method: 'GET', headers: authHeaders });
  const rbac = await demoFetch<RbacMe>('/rbac/me', { method: 'GET', headers: authHeaders });
  await setRequestContext({
    organisationId: rbac.active_organisation_id,
    role: rbac.active_role,
  });

  return {
    accessToken: login.access_token,
    email: login.email,
    session: { auth, rbac },
  };
}
