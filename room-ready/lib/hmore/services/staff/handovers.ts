import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

import { assertCanUseCaseload } from './access';

export type HandoverPriority = 'low' | 'normal' | 'high' | 'urgent';
export type HandoverStatus = 'draft' | 'submitted' | 'acknowledged' | 'completed' | 'cancelled';

export interface Handover {
  id: string;
  tenant_id: string;
  summary: string;
  status: HandoverStatus;
  priority: HandoverPriority;
  case_updates: string | null;
  outstanding_tasks: string | null;
  follow_up_actions: string | null;
  created_by_user_id: string;
  recipient_user_id: string;
  handover_at: string;
  tenant_preferred_name?: string | null;
}

export interface HandoverCreateInput {
  tenant_id: string;
  recipient_user_id: string;
  summary: string;
  case_updates?: string | null;
  outstanding_tasks?: string | null;
  follow_up_actions?: string | null;
  priority?: HandoverPriority;
  submit?: boolean;
}

export function listHandovers(
  actorRole: string | null | undefined,
  query?: { page?: number; page_size?: number; tenant_id?: string; status?: string; pending_only?: boolean },
): Promise<Page<Handover>> {
  assertCanUseCaseload(actorRole);
  return hmoreFetch<Page<Handover>>('/handovers', { method: 'GET', query });
}

export function createHandover(actorRole: string | null | undefined, body: HandoverCreateInput): Promise<Handover> {
  assertCanUseCaseload(actorRole);
  return hmoreFetch<Handover>('/handovers', { method: 'POST', body });
}