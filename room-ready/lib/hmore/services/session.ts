import { getStoredAccessToken } from '@/lib/hmoreAuth0';
import { HmoreApiError, hmoreFetch } from '@/lib/hmore/client';
import { setRequestContext } from '@/lib/hmore/requestContext';
import type { AuthMe, RbacMe } from '@/lib/hmore/types';

export interface HmoreSession {
  auth: AuthMe;
  rbac: RbacMe;
}

function resolveOrganisationId(rbac: RbacMe): string | null {
  if (rbac.active_organisation_id) return rbac.active_organisation_id;
  const membership = (rbac.memberships ?? []).find((item) => item.organisation_id);
  return membership?.organisation_id ?? null;
}

async function readSession(accessToken?: string): Promise<HmoreSession> {
  const token = accessToken ?? (await getStoredAccessToken());
  if (!token) {
    throw new HmoreApiError(401, 'Please sign in again');
  }
  const headers = { Authorization: `Bearer ${token}` };
  const auth = await hmoreFetch<AuthMe>('/auth/me', { headers });
  const rbac = await hmoreFetch<RbacMe>('/rbac/me', { headers });
  await setRequestContext({
    organisationId: resolveOrganisationId(rbac),
    role: rbac.active_role,
  });
  return { auth, rbac };
}

/** Loads Auth0-backed FastAPI identity and stores org/role headers for later calls. */
export async function loadHmoreSession(accessToken?: string): Promise<HmoreSession> {
  try {
    return await readSession(accessToken);
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 403 || error.status === 400)) {
      await setRequestContext({ organisationId: null, role: null });
      return readSession(accessToken);
    }
    throw error;
  }
}
