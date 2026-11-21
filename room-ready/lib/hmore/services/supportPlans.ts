import { HmoreApiError, hmoreFetch } from '@/lib/hmore/client';
import type { Page, SupportPlan } from '@/lib/hmore/types';

/** Tenant self-service plans. Read only. */
export async function listOwnSupportPlans(): Promise<Page<SupportPlan>> {
  try {
    return await hmoreFetch<Page<SupportPlan>>('/tenant/support-plans', {
      method: 'GET',
      query: { page: 1, page_size: 20 },
    });
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 404 || error.status === 403)) {
      return { items: [], page: 1, page_size: 20, total: 0 };
    }
    throw error;
  }
}

export function getOwnSupportPlan(planId: string): Promise<SupportPlan> {
  return hmoreFetch<SupportPlan>(`/tenant/support-plans/${planId}`, { method: 'GET' });
}
