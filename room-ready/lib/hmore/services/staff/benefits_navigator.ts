import { hmoreFetch } from '@/lib/hmore/client';

export function getBenefitsCommunitySupport(): Promise<Record<string, unknown>[]> {
  return hmoreFetch<Record<string, unknown>[]>('/benefits-navigator/community-support', { method: 'GET' });
}
