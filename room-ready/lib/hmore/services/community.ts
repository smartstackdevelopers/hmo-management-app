import { hmoreFetch } from '@/lib/hmore/client';
import type { CommunityServiceItem } from '@/lib/hmore/types';

export type CommunityServicePage = {
  items: CommunityServiceItem[];
  page: number;
  page_size: number;
  total: number;
};

export function communityItemsFromResponse(
  response: { items?: CommunityServiceItem[] } | null | undefined,
): CommunityServiceItem[] {
  return response?.items ?? [];
}

export async function listCommunityServices(query?: {
  q?: string;
  category?: string;
  page?: number;
  page_size?: number;
  has_opening_hours?: boolean;
  has_eligibility?: boolean;
}): Promise<CommunityServiceItem[]> {
  const response = await hmoreFetch<CommunityServicePage>('/community-services', {
    method: 'GET',
    query,
  });
  return communityItemsFromResponse(response);
}

export async function listCommunityServicesPage(query?: {
  q?: string;
  category?: string;
  page?: number;
  page_size?: number;
  has_opening_hours?: boolean;
  has_eligibility?: boolean;
}): Promise<CommunityServicePage> {
  const response = await hmoreFetch<CommunityServicePage>('/community-services', {
    method: 'GET',
    query,
  });
  return {
    items: communityItemsFromResponse(response),
    page: response?.page ?? 1,
    page_size: response?.page_size ?? 50,
    total: response?.total ?? 0,
  };
}

export async function getCommunityService(serviceId: string): Promise<CommunityServiceItem> {
  return hmoreFetch<CommunityServiceItem>(`/community-services/${serviceId}`, {
    method: 'GET',
  });
}
