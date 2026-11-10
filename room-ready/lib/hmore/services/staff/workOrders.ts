import type { MaintenanceRequest, Page } from '@/lib/hmore/types';
import {
  addMaintenanceNote,
  completeMaintenance,
  listMaintenance,
  listMaintenanceVisits,
  transitionMaintenance,
  uploadMaintenancePhoto,
  type MaintenanceVisit,
} from '@/lib/hmore/services/maintenance';

/** Assigned work orders. The API scopes a contractor to their own requests. This module does not call caseload. */
export function listAssignedWorkOrders(): Promise<Page<MaintenanceRequest>> {
  return listMaintenance({ page: 1, page_size: 50 });
}

export function listWorkOrderVisits(requestId: string): Promise<MaintenanceVisit[]> {
  return listMaintenanceVisits(requestId);
}

export function updateWorkOrderStatus(requestId: string, status: 'in_progress' | 'on_hold', note?: string) {
  return transitionMaintenance(requestId, { status, note });
}

export function completeWorkOrder(requestId: string, workNotes: string) {
  return completeMaintenance(requestId, { work_notes: workNotes });
}

export function addWorkOrderNote(requestId: string, body: string) {
  return addMaintenanceNote(requestId, body);
}

export function uploadWorkOrderPhoto(
  requestId: string,
  file: { uri: string; name: string; mimeType: string },
  caption?: string,
) {
  return uploadMaintenancePhoto(requestId, file, caption, 'completion');
}
