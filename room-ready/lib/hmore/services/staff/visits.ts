import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

export interface StaffVisit {
  id: string;
  tenant_id: string;
  assigned_staff_user_id: string;
  scheduled_at: string;
  visit_type: string;
  purpose: string;
  location: string | null;
  status: string;
  outcome: string | null;
  notes: string | null;
  updated_at?: string;
}

export function listVisits(query?: { page?: number; page_size?: number; status?: string }): Promise<Page<StaffVisit>> {
  return hmoreFetch<Page<StaffVisit>>('/visits', { method: 'GET', query: { page: 1, page_size: 50, ...query } });
}

export function updateVisit(
  visitId: string,
  body: { status?: string; outcome?: string | null; notes?: string | null; if_match_updated_at?: string },
  idempotencyKey?: string,
): Promise<StaffVisit> {
  return hmoreFetch<StaffVisit>(`/visits/${visitId}`, { method: 'PATCH', body, idempotencyKey });
}
