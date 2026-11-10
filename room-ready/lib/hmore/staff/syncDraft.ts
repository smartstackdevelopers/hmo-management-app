import { HmoreApiError } from '@/lib/hmore/client';
import type { StaffDraft } from '@/lib/hmore/staff/offlineDrafts';
import { createDailyLog, type DailyLogInput } from '@/lib/hmore/services/staff/dailyLogs';
import { updateTask } from '@/lib/hmore/services/staff/tasks';
import { updateVisit } from '@/lib/hmore/services/staff/visits';
import { completeWorkOrder, updateWorkOrderStatus } from '@/lib/hmore/services/staff/workOrders';

function text(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

/** Sends the draft payload. `clientRequestId` stays on the draft and is not posted. */
export async function submitStaffDraft(draft: StaffDraft): Promise<{ status: number; error?: string }> {
  try {
    if (draft.type === 'daily_log') {
      const created = await createDailyLog(draft.payload as unknown as DailyLogInput);
      return created?.id ? { status: 201 } : { status: 0, error: 'The server did not confirm the note.' };
    }
    if (draft.type === 'visit_update') {
      const updated = await updateVisit(text(draft.payload.visit_id), {
        status: text(draft.payload.status) || undefined,
        outcome: text(draft.payload.outcome) || null,
        notes: text(draft.payload.notes) || null,
      });
      return updated?.id ? { status: 200 } : { status: 0, error: 'The server did not confirm the visit.' };
    }
    if (draft.type === 'task_update') {
      const updated = await updateTask(text(draft.payload.task_id), { status: text(draft.payload.status) || undefined });
      return updated?.id ? { status: 200 } : { status: 0, error: 'The server did not confirm the task.' };
    }
    const requestId = text(draft.payload.request_id);
    if (draft.payload.action === 'complete') {
      const updated = await completeWorkOrder(requestId, text(draft.payload.work_notes));
      return updated?.id ? { status: 200 } : { status: 0, error: 'The server did not confirm the work order.' };
    }
    const updated = await updateWorkOrderStatus(
      requestId,
      text(draft.payload.status) === 'on_hold' ? 'on_hold' : 'in_progress',
      text(draft.payload.note) || undefined,
    );
    return updated?.id ? { status: 200 } : { status: 0, error: 'The server did not confirm the work order.' };
  } catch (error) {
    if (error instanceof HmoreApiError) return { status: error.status, error: error.detail };
    return { status: 0, error: 'Could not reach HMore. The draft is still on this device.' };
  }
}
