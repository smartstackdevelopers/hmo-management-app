import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

import { assertCanUseCaseload } from './access';

export interface CaseAssignment {
  id: string;
  tenant_id: string;
  support_worker_user_id: string;
  status: string;
  tenant_preferred_name: string | null;
  tenant_full_name: string | null;
  assignment_notes: string | null;
  recent_log_count?: number | null;
  pending_handover_count?: number | null;
}

export interface CaseTenant {
  id: string;
  preferred_name: string | null;
  full_name: string | null;
  tenancy_reference: string | null;
  status: string | null;
}

export interface CaseDetail {
  tenant: CaseTenant;
  assignments: CaseAssignment[];
  recent_logs: { id: string; summary: string; log_date: string; status: string; activity_category: string }[];
  recent_handovers: { id: string; summary: string; status: string }[];
}

export function listCaseload(
  actorRole: string | null | undefined,
  query?: { page?: number; page_size?: number; q?: string; status?: string },
): Promise<Page<CaseAssignment>> {
  assertCanUseCaseload(actorRole);
  return hmoreFetch<Page<CaseAssignment>>('/caseload', { method: 'GET', query });
}

export function getCaseDetail(actorRole: string | null | undefined, tenantId: string): Promise<CaseDetail> {
  assertCanUseCaseload(actorRole);
  return hmoreFetch<CaseDetail>(`/caseload/tenants/${tenantId}`, { method: 'GET' });
}

export function listCaseAssignments(
  actorRole: string | null | undefined,
): Promise<Page<CaseAssignment>> {
  return listCaseload(actorRole, { page: 1, page_size: 50, status: 'active' });
}
