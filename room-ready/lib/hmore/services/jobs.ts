import { hmoreFetch } from '@/lib/hmore/client';
import type { OpportunityItem } from '@/lib/hmore/types';

export function opportunityItemsFromResponse(
  response: { items?: OpportunityItem[] } | null | undefined,
): OpportunityItem[] {
  return response?.items ?? [];
}

export async function listOpportunities(query?: {
  kind?: string;
  q?: string;
}): Promise<OpportunityItem[]> {
  const response = await hmoreFetch<{ items?: OpportunityItem[] }>('/opportunities', {
    method: 'GET',
    query,
  });
  return opportunityItemsFromResponse(response);
}
