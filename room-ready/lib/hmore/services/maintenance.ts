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

export async function uploadMaintenancePhoto(
  requestId: string,
  file: { uri: string; name: string; mimeType: string },
  caption?: string,
): Promise<MaintenanceRequest> {
  const formData = new FormData();
  formData.append('upload', { uri: file.uri, name: file.name, type: file.mimeType } as unknown as Blob);
  formData.append('photo_kind', 'problem');
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
