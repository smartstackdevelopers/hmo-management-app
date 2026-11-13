import { hmoreFetch } from '@/lib/hmore/client';

export function getEngagementDashboard(): Promise<Record<string, unknown>> {
  return hmoreFetch<Record<string, unknown>>('/tenant-engagement/tenant/dashboard', { method: 'GET' });
}
