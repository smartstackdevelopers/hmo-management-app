import { hmoreFetch } from '@/lib/hmore/client';
import type { CommunityServiceItem } from '@/lib/hmore/types';

export function communityItemsFromResponse(
  response: { items?: CommunityServiceItem[] } | null | undefined,
): CommunityServiceItem[] {
  return response?.items ?? [];
}

export async function listCommunityServices(query?: {
  q?: string;
  category?: string;
}): Promise<CommunityServiceItem[]> {
  const response = await hmoreFetch<{ items?: CommunityServiceItem[] }>('/community-services', {
    method: 'GET',
    query,
  });
  return communityItemsFromResponse(response);
}
