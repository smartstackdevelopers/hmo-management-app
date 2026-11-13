import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

export interface SafeguardingAlertRecord {
  id: string;
  reference_number: string;
  status: string;
  priority: string;
  description: string;
  tenant_id: string | null;
  assigned_user_id: string | null;
  requires_human_review: boolean;
  created_at: string;
}

export function listSafeguardingAlerts(): Promise<SafeguardingAlertRecord[]> {
  return hmoreFetch<SafeguardingAlertRecord[]>('/safeguarding-alerts/alerts', {
    method: 'GET',
  });
}

export function getSafeguardingDashboard(): Promise<Record<string, unknown>> {
  return hmoreFetch<Record<string, unknown>>('/safeguarding-alerts/dashboard', { method: 'GET' });
}
