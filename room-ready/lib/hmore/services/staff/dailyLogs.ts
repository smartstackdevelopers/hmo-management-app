import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

export const ACTIVITY_CATEGORIES = [
  'welfare_check',
  'keywork',
  'housing',
  'health',
  'safeguarding',
  'appointment',
  'phone_call',
  'email',
  'other',
] as const;

export const INTERACTION_TYPES = ['in_person', 'phone', 'video', 'message', 'collateral', 'other'] as const;

export interface DailyLogInput {
  tenant_id: string;
  activity_category: string;
  summary: string;
  notes: string;
  interaction_type?: string | null;
  follow_up_required?: boolean;
  next_action?: string | null;
  log_date?: string | null;
}

export interface DailyLog {
  id: string;
  tenant_id: string;
  log_date: string;
  activity_category: string;
  summary: string;
  notes: string;
  interaction_type: string | null;
  follow_up_required: boolean;
  next_action: string | null;
  status: string;
  created_at: string;
}

export function listDailyLogs(query?: { page?: number; page_size?: number; tenant_id?: string }): Promise<Page<DailyLog>> {
  return hmoreFetch<Page<DailyLog>>('/daily-logs', { method: 'GET', query });
}

export function createDailyLog(body: DailyLogInput): Promise<DailyLog> {
  return hmoreFetch<DailyLog>('/daily-logs', { method: 'POST', body });
}
