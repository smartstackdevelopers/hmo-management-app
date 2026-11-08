import { hmoreFetch } from '@/lib/hmore/client';
import type { AnnouncementDetail, AnnouncementSummary, InboxMessage, MessageDetail, Page } from '@/lib/hmore/types';

export function listInbox(): Promise<Page<InboxMessage>> {
  return hmoreFetch<Page<InboxMessage>>('/communications/messages/inbox', {
    method: 'GET',
    query: { page: 1, page_size: 50 },
  });
}

export function getMessage(messageId: string): Promise<MessageDetail> {
  return hmoreFetch<MessageDetail>(`/communications/messages/${messageId}`, { method: 'GET' });
}

export function markMessageRead(messageId: string): Promise<unknown> {
  return hmoreFetch(`/communications/messages/${messageId}/read`, {
    method: 'PATCH',
    body: { read: true },
  });
}

export function listAnnouncements(): Promise<AnnouncementSummary[]> {
  return hmoreFetch<AnnouncementSummary[]>('/communications/announcements', { method: 'GET' });
}

export function getAnnouncement(id: string): Promise<AnnouncementDetail> {
  return hmoreFetch<AnnouncementDetail>(`/communications/announcements/${id}`, { method: 'GET' });
}
