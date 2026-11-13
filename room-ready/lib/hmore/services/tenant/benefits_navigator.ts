import { hmoreFetch } from '@/lib/hmore/client';

export function getBenefitsDashboard(): Promise<Record<string, unknown>> {
  return hmoreFetch<Record<string, unknown>>('/benefits-navigator/tenant/dashboard', { method: 'GET' });
}

export function searchBenefitsNavigator(): Promise<Record<string, unknown>[]> {
  return hmoreFetch<Record<string, unknown>[]>('/benefits-navigator/search', { method: 'GET' });
}
