import { HmoreApiError, hmoreFetch, hmoreRequestResponse } from '@/lib/hmore/client';
import type {
  MaintenanceCategory,
  MaintenanceCreateInput,
  MaintenanceRequest,
  Page,
} from '@/lib/hmore/types';

export function listMaintenance(query?: {
  page?: number;
  page_size?: number;
  status?: string;
}): Promise<Page<MaintenanceRequest>> {
  return hmoreFetch<Page<MaintenanceRequest>>('/maintenance', { method: 'GET', query });
}

export function getMaintenance(id: string): Promise<MaintenanceRequest> {
  return hmoreFetch<MaintenanceRequest>(`/maintenance/${id}`, { method: 'GET' });
}

export function createMaintenance(body: MaintenanceCreateInput): Promise<MaintenanceRequest> {
  return hmoreFetch<MaintenanceRequest>('/maintenance', { method: 'POST', body });
}

export function listMaintenanceCategories(): Promise<MaintenanceCategory[]> {
  return hmoreFetch<MaintenanceCategory[]>('/maintenance/categories', { method: 'GET' });
}

export interface MaintenanceVisit {
  id: string;
  request_id: string;
  assignee_user_id: string | null;
  scheduled_at: string;
  timezone: string;
  status: string;
  work_notes: string | null;
  cancel_reason: string | null;
  completed_at: string | null;
}

export function listMaintenanceVisits(requestId: string): Promise<MaintenanceVisit[]> {
  return hmoreFetch<MaintenanceVisit[]>(`/maintenance/${requestId}/visits`, { method: 'GET' });
}

export function transitionMaintenance(
  requestId: string,
  body: { status: string; note?: string },
): Promise<MaintenanceRequest> {
  return hmoreFetch<MaintenanceRequest>(`/maintenance/${requestId}/transition`, { method: 'POST', body });
}

export function completeMaintenance(
  requestId: string,
  body: { work_notes: string; completion_summary?: string },
): Promise<MaintenanceRequest> {
  return hmoreFetch<MaintenanceRequest>(`/maintenance/${requestId}/complete`, { method: 'POST', body });
}

export function addMaintenanceNote(requestId: string, body: string): Promise<{ id: string; body: string }> {
  return hmoreFetch(`/maintenance/${requestId}/notes`, {
    method: 'POST',
    body: { body, visibility: 'internal' },
  });
}

export function scheduleMaintenanceVisit(
  requestId: string,
  body: { scheduled_at: string; timezone?: string },
): Promise<MaintenanceVisit> {
  return hmoreFetch<MaintenanceVisit>(`/maintenance/${requestId}/schedule`, { method: 'POST', body });
}

export function completeMaintenanceVisit(
  requestId: string,
  visitId: string,
  body: { work_notes?: string; missed?: boolean },
): Promise<MaintenanceVisit> {
  return hmoreFetch<MaintenanceVisit>(`/maintenance/${requestId}/visits/${visitId}/complete`, {
    method: 'POST',
    body,
  });
}

export async function uploadMaintenancePhoto(
  requestId: string,
  file: { uri: string; name: string; mimeType: string },
  caption?: string,
  photoKind: 'problem' | 'completion' = 'problem',
): Promise<MaintenanceRequest> {
  const formData = new FormData();
  formData.append('upload', { uri: file.uri, name: file.name, type: file.mimeType } as unknown as Blob);
  formData.append('photo_kind', photoKind);
  if (caption) formData.append('caption', caption);
  const response = await hmoreRequestResponse(`/maintenance/${requestId}/files/upload`, {
    method: 'POST',
    formData,
  });
  const data = (await response.json().catch(() => ({}))) as { detail?: unknown };
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Could not upload the photo';
    throw new HmoreApiError(response.status, detail);
  }
  return data as MaintenanceRequest;
}
