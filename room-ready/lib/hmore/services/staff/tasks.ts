import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

export interface StaffTask {
  id: string;
  title: string;
  description: string | null;
  assigned_user_id: string;
  tenant_id: string | null;
  priority: string;
  due_at: string | null;
  status: string;
  overdue: boolean;
  updated_at?: string;
}

export function listOwnTasks(userId: string): Promise<Page<StaffTask>> {
  return hmoreFetch<Page<StaffTask>>('/tasks', {
    method: 'GET',
    query: { page: 1, page_size: 50, assigned_user_id: userId },
  });
}

export function updateTask(
  taskId: string,
  body: { status?: string; description?: string | null; if_match_updated_at?: string },
  idempotencyKey?: string,
): Promise<StaffTask> {
  return hmoreFetch<StaffTask>(`/tasks/${taskId}`, { method: 'PATCH', body, idempotencyKey });
}
