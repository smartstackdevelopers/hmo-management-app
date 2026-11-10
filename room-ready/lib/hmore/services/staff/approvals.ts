import { hmoreFetch } from '@/lib/hmore/client';
import type { Page } from '@/lib/hmore/types';

export interface ApprovalInboxItem {
  reference: string;
  source_type: string;
  source_id: string;
  title: string;
  status: string;
  priority: string | null;
  related_url_path: string | null;
}

export function listApprovalInbox(): Promise<Page<ApprovalInboxItem>> {
  return hmoreFetch<Page<ApprovalInboxItem>>('/org-workflows/approvals/inbox', {
    method: 'GET',
    query: { page: 1, page_size: 50 },
  });
}

export function decideApproval(
  sourceType: string,
  sourceId: string,
  body: { action: 'approve' | 'reject' | 'request_information'; reason?: string | null },
): Promise<unknown> {
  return hmoreFetch(`/org-workflows/approvals/${sourceType}/${sourceId}/decide`, { method: 'POST', body });
}
