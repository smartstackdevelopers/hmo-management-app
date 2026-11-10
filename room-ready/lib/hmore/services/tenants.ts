import { HmoreApiError, hmoreFetch } from '@/lib/hmore/client';
import type { Page, Tenant, TenantSelf } from '@/lib/hmore/types';

const SELF_PATCH_FIELDS = ['preferred_name', 'phone'] as const;

export type TenantSelfPatch = {
  preferred_name?: string;
  phone?: string | null;
};

/** Copies only preferred_name and phone. Every other key is dropped. */
export function tenantSelfPatchBody(input: Record<string, unknown>): TenantSelfPatch {
  const body: TenantSelfPatch = {};
  if (typeof input.preferred_name === 'string') body.preferred_name = input.preferred_name;
  if (typeof input.phone === 'string' || input.phone === null) body.phone = input.phone;
  return body;
}

export function listOwnTenants(): Promise<Page<Tenant>> {
  return hmoreFetch<Page<Tenant>>('/tenants', { method: 'GET', query: { page: 1, page_size: 20 } });
}

export async function getOwnTenant(userId: string): Promise<Tenant | null> {
  const page = await listOwnTenants();
  return page.items.find((row) => row.user_id === userId) ?? null;
}

export async function getOwnProfile(): Promise<TenantSelf | null> {
  try {
    return await hmoreFetch<TenantSelf>('/tenant/me', { method: 'GET' });
  } catch (error) {
    if (error instanceof HmoreApiError && error.status === 404) return null;
    throw error;
  }
}

export function patchOwnTenant(input: Record<string, unknown>): Promise<TenantSelf> {
  return hmoreFetch<TenantSelf>('/tenant/me', {
    method: 'PATCH',
    body: tenantSelfPatchBody(input),
  });
}

export { SELF_PATCH_FIELDS };
