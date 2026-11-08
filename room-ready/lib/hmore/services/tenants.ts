import { hmoreFetch } from '@/lib/hmore/client';
import type { Page, Tenant } from '@/lib/hmore/types';

/**
 * Housing profile for the signed-in tenant.
 * GET /tenants is scoped to the caller's own row. Tenants cannot PATCH /tenants,
 * so this module does not expose an update.
 */
export function listOwnTenants(): Promise<Page<Tenant>> {
  return hmoreFetch<Page<Tenant>>('/tenants', { method: 'GET', query: { page: 1, page_size: 20 } });
}

export async function getOwnTenant(userId: string): Promise<Tenant | null> {
  const page = await listOwnTenants();
  return page.items.find((row) => row.user_id === userId) ?? null;
}
