import { hmoreFetch } from '@/lib/hmore/client';
import type { Page, SupportPlan } from '@/lib/hmore/types';

/** Tenant self-service plans. Read only. */
export function listOwnSupportPlans(): Promise<Page<SupportPlan>> {
  return hmoreFetch<Page<SupportPlan>>('/tenant/support-plans', {
    method: 'GET',
    query: { page: 1, page_size: 20 },
  });
}

export function getOwnSupportPlan(planId: string): Promise<SupportPlan> {
  return hmoreFetch<SupportPlan>(`/tenant/support-plans/${planId}`, { method: 'GET' });
}
