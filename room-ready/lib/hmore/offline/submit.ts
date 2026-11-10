import { HmoreApiError, conflictUpdatedAt } from '@/lib/hmore/client';
import { idempotencyHeaders } from '@/lib/hmore/offline/syncEngine';
import type { OfflineDraft } from '@/lib/hmore/offline/store';
import type { SyncAck } from '@/lib/hmore/offline/syncEngine';
import {
  addMaintenanceNote,
  completeMaintenance,
  createMaintenance,
  patchMaintenance,
  transitionMaintenance,
  uploadMaintenancePhoto,
} from '@/lib/hmore/services/maintenance';
import { createDailyLog, type DailyLogInput } from '@/lib/hmore/services/staff/dailyLogs';
import { updateTask } from '@/lib/hmore/services/staff/tasks';
import { updateVisit } from '@/lib/hmore/services/staff/visits';

function text(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function matchStamp(draft: OfflineDraft): string | undefined {
  const fromPayload = draft.payload.if_match_updated_at;
  if (typeof fromPayload === 'string' && fromPayload) return fromPayload;
  return draft.serverUpdatedAt;
}

function ack(status: number, serverResourceId?: string, serverUpdatedAt?: string): SyncAck {
  if (!serverResourceId) return { status: 0, error: 'The server did not confirm the record.' };
  return { status, serverResourceId, serverUpdatedAt };
}

function failure(error: unknown): SyncAck {
  if (error instanceof HmoreApiError) {
    return { status: error.status, error: error.detail, serverUpdatedAt: conflictUpdatedAt(error) };
  }
  return { status: 0, error: 'Could not reach HMore. The draft is still on this device.' };
}

/**
 * Sends one draft. The Idempotency-Key is the draft's clientRequestId.
 * Passwords are never read from the payload. Approval decisions are not sent.
 */
export async function submitOfflineDraft(draft: OfflineDraft): Promise<SyncAck> {
  const headers = idempotencyHeaders(draft);
  const key = headers['Idempotency-Key'];
  try {
    if (draft.type === 'daily_log') {
      const created = await createDailyLog(draft.payload as unknown as DailyLogInput, key);
      return ack(201, created?.id);
    }
    if (draft.type === 'visit_update') {
      const updated = await updateVisit(
        text(draft.payload.visit_id),
        {
          status: text(draft.payload.status) || undefined,
          outcome: text(draft.payload.outcome) || null,
          notes: text(draft.payload.notes) || null,
          if_match_updated_at: matchStamp(draft),
        },
        key,
      );
      return ack(200, updated?.id, updated?.updated_at);
    }
    if (draft.type === 'task_update') {
      const updated = await updateTask(
        text(draft.payload.task_id),
        { status: text(draft.payload.status) || undefined, if_match_updated_at: matchStamp(draft) },
        key,
      );
      return ack(200, updated?.id, updated?.updated_at);
    }
    if (draft.type === 'repair_create') {
      const created = await createMaintenance(
        {
          title: text(draft.payload.title),
          description: text(draft.payload.description),
          category_code: text(draft.payload.category_code) || 'general',
          priority: (text(draft.payload.priority) || 'normal') as 'low' | 'normal' | 'high' | 'urgent',
          property_id: text(draft.payload.property_id),
          room_id: text(draft.payload.room_id) || null,
          tenant_id: text(draft.payload.tenant_id) || null,
        },
        key,
      );
      return ack(201, created?.id, created?.updated_at);
    }
    const requestId = text(draft.payload.request_id) || draft.serverResourceId || '';
    if (draft.payload.action === 'note') {
      const noted = await addMaintenanceNote(requestId, text(draft.payload.note || draft.payload.body), key, matchStamp(draft));
      return ack(201, noted?.id || requestId);
    }
    if (draft.payload.action === 'patch') {
      const updated = await patchMaintenance(
        requestId,
        {
          title: text(draft.payload.title) || undefined,
          description: text(draft.payload.description) || undefined,
          category_code: text(draft.payload.category_code) || undefined,
          if_match_updated_at: matchStamp(draft),
        },
        key,
      );
      return ack(200, updated?.id, updated?.updated_at);
    }
    if (draft.payload.action === 'complete') {
      const updated = await completeMaintenance(
        requestId,
        { work_notes: text(draft.payload.work_notes), if_match_updated_at: matchStamp(draft) },
        key,
      );
      return ack(200, updated?.id, updated?.updated_at);
    }
    const updated = await transitionMaintenance(
      requestId,
      {
        status: text(draft.payload.status) === 'on_hold' ? 'on_hold' : 'in_progress',
        note: text(draft.payload.note) || undefined,
        if_match_updated_at: matchStamp(draft),
      },
      key,
    );
    return ack(200, updated?.id, updated?.updated_at);
  } catch (error) {
    return failure(error);
  }
}

export async function uploadDraftAttachment(draft: OfflineDraft, uri: string, resourceId: string): Promise<void> {
  const files = Array.isArray(draft.payload.local_files) ? draft.payload.local_files : [];
  const meta = files.find((item) => !!item && typeof item === 'object' && (item as { uri?: unknown }).uri === uri) as
    | { name?: string; mimeType?: string }
    | undefined;
  const kind = draft.type === 'work_order_update' ? 'completion' : 'problem';
  await uploadMaintenancePhoto(
    resourceId,
    { uri, name: meta?.name || 'photo.jpg', mimeType: meta?.mimeType || 'image/jpeg' },
    undefined,
    kind,
  );
}
