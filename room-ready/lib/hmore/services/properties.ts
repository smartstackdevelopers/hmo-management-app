import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';
import type { PropertyItem } from '@/lib/api';

export type HmoreProperty = {
  id: string;
  name: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  region?: string | null;
  postcode: string;
  country_code?: string;
  status?: string;
  notes?: string | null;
  landlord_user_id?: string | null;
};

export function listProperties(page = 1, pageSize = 50): Promise<Page<HmoreProperty>> {
  return hmoreFetch<Page<HmoreProperty>>('/properties', {
    method: 'GET',
    query: { page, page_size: pageSize },
  });
}

/** Map FastAPI property records onto the mobile PropertyItem shell shape. */
export function mapHmoreProperty(row: HmoreProperty): PropertyItem {
  return {
    id: String(row.id),
    name: row.name,
    addressLine1: row.address_line1,
    addressLine2: row.address_line2 ?? undefined,
    city: row.city,
    county: row.region ?? undefined,
    postcode: row.postcode,
    maxOccupants: 0,
    description: row.notes ?? undefined,
    rooms: [],
    _count: { maintenance: 0 },
  };
}
