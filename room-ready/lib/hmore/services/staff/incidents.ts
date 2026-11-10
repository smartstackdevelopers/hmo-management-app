import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

export interface IncidentInput {
  title: string;
  category?: string;
  description: string;
  occurred_at: string;
  tenant_id?: string | null;
  location?: string | null;
  severity?: 'low' | 'normal' | 'high' | 'critical';
  immediate_actions?: string | null;
  submit?: boolean;
}

export interface IncidentRecord {
  id: string;
  reference_number: string;
  title: string;
  category: string;
  description: string;
  occurred_at: string;
  severity: string;
  status: string;
  tenant_id: string | null;
  location: string | null;
}

export function listIncidents(): Promise<Page<IncidentRecord>> {
  return hmoreFetch<Page<IncidentRecord>>('/incidents', { method: 'GET', query: { page: 1, page_size: 50 } });
}

export function getIncident(id: string): Promise<IncidentRecord> {
  return hmoreFetch<IncidentRecord>(`/incidents/${id}`, { method: 'GET' });
}

export function createIncident(body: IncidentInput): Promise<IncidentRecord> {
  return hmoreFetch<IncidentRecord>('/incidents', { method: 'POST', body });
}
