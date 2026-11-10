import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

export interface StaffShift {
  id: string;
  staff_user_id: string;
  shift_date: string;
  starts_at: string;
  ends_at: string;
  timezone: string;
  shift_type: string;
  location: string | null;
  notes: string | null;
  status: string;
}

export function listOwnShifts(staffUserId: string): Promise<Page<StaffShift>> {
  return hmoreFetch<Page<StaffShift>>('/shifts', {
    method: 'GET',
    query: { page: 1, page_size: 50, staff_user_id: staffUserId },
  });
}
