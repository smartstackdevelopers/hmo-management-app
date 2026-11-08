import { HmoreApiError, hmoreFetch } from '@/lib/hmore/client';
import { setRequestContext } from '@/lib/hmore/requestContext';
import type { AuthMe, RbacMe } from '@/lib/hmore/types';

export interface HmoreSession {
  auth: AuthMe;
  rbac: RbacMe;
}

async function readSession(): Promise<HmoreSession> {
  const auth = await hmoreFetch<AuthMe>('/auth/me');
  const rbac = await hmoreFetch<RbacMe>('/rbac/me');
  await setRequestContext({
    organisationId: rbac.active_organisation_id,
    role: rbac.active_role,
  });
  return { auth, rbac };
}

/** Loads Auth0-backed FastAPI identity and stores org/role headers for later calls. */
export async function loadHmoreSession(): Promise<HmoreSession> {
  try {
    return await readSession();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 403 || error.status === 400)) {
      await setRequestContext({ organisationId: null, role: null });
      return readSession();
    }
    throw error;
  }
}
