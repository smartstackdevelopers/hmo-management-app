import { HmoreApiError, hmoreFetch } from '@/lib/hmore/client';
import type { TenantHousing } from '@/lib/hmore/types';

export async function getOwnHousing(): Promise<TenantHousing | null> {
  try {
    return await hmoreFetch<TenantHousing>('/tenant/me/housing', { method: 'GET' });
  } catch (error) {
    if (error instanceof HmoreApiError && error.status === 404) return null;
    throw error;
  }
}

/** Property id from the housing payload. Null when nothing is assigned. */
export function assignedPropertyId(housing: TenantHousing | null | undefined): string | null {
  return housing?.property?.id ?? null;
}

/** Address lines from the assigned property only. Null when property is null. */
export function formatAssignedAddress(housing: TenantHousing | null | undefined): string | null {
  const property = housing?.property;
  if (!property) return null;
  const parts = [property.address_line1, property.address_line2, property.city, property.postcode].filter(
    (part): part is string => typeof part === 'string' && part.trim().length > 0,
  );
  return parts.length > 0 ? parts.join(', ') : null;
}
