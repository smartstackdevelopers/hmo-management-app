import { hmoreFetch } from '@/lib/hmore/client';
import type { Appointment, Page, TimelineItem } from '@/lib/hmore/types';

export function listAppointments(tenantId: string): Promise<Page<Appointment>> {
  return hmoreFetch<Page<Appointment>>(`/tenants/${tenantId}/timeline/appointments`, {
    method: 'GET',
    query: { page: 1, page_size: 50 },
  });
}

export function getTimeline(tenantId: string): Promise<Page<TimelineItem>> {
  return hmoreFetch<Page<TimelineItem>>(`/tenants/${tenantId}/timeline`, {
    method: 'GET',
    query: { page: 1, page_size: 20, sort: 'newest' },
  });
}
