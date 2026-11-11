import { hmoreFetch } from '@/lib/hmore/client';

export type NearbyService = {
  id: string;
  category: string;
  name: string;
  description: string | null;
  address_line: string | null;
  opening_days?: string | null;
  opening_hours: string | null;
  eligibility: string | null;
  referral_requirements?: string | null;
  contact: string | null;
  service_instructions?: string | null;
  clothing_service_type?: string | null;
  verification_status: string;
  verified_at?: string | null;
  updated_at?: string | null;
  latitude: number;
  longitude: number;
  distance_km: number;
  distance_miles: number;
};

export type NearbySearchResult = {
  postcode: string;
  latitude: number;
  longitude: number;
  radius_km: number;
  sort: string;
  page: number;
  page_size: number;
  total: number;
  items: NearbyService[];
};

export type OutdatedReport = {
  id: string;
  service_id: string;
  reason: string;
  details: string | null;
  status: string;
  created_at: string;
};

export async function validatePostcode(postcode: string) {
  return hmoreFetch<{
    postcode: string;
    latitude: number;
    longitude: number;
    provider: string;
  }>('/help-near-me/validate-postcode', {
    method: 'GET',
    query: { postcode },
  });
}

export async function searchNearby(query: {
  postcode: string;
  category?: string;
  radius_km?: number;
  sort?: 'distance' | 'name';
  page?: number;
  page_size?: number;
}): Promise<NearbySearchResult> {
  return hmoreFetch<NearbySearchResult>('/help-near-me/nearby', {
    method: 'GET',
    query,
  });
}

export async function submitOutdatedReport(body: {
  service_id: string;
  reason: string;
  details?: string | null;
}): Promise<OutdatedReport> {
  return hmoreFetch<OutdatedReport>('/help-near-me/reports', {
    method: 'POST',
    body,
  });
}
