import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';

import { Feedback, StaffPage, StatusRow, staffLabel, statusTone } from '@/components/staff/ui';
import { HmoreApiError, hmoreErrorMessage } from '@/lib/hmore/client';
import { staffAlertHref } from '@/lib/hmore/staff/alerts';
import { getMessage, listAnnouncements, listInbox, markMessageRead } from '@/lib/hmore/services/communications';
import type { AnnouncementSummary, InboxMessage, Page } from '@/lib/hmore/types';

async function safeListInbox(): Promise<Page<InboxMessage>> {
  try {
    return await listInbox();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 403 || error.status === 404 || error.status === 400)) {
      return { items: [], page: 1, page_size: 50, total: 0 };
    }
    throw error;
  }
}

async function safeListAnnouncements(): Promise<AnnouncementSummary[]> {
  try {
    return await listAnnouncements();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 403 || error.status === 404 || error.status === 400)) {
      return [];
    }
    throw error;
  }
}

export function StaffAlertList() {
  const client = useQueryClient();
  const inbox = useQuery({ queryKey: ['hmore', 'inbox'], queryFn: safeListInbox });
  const announcements = useQuery({ queryKey: ['hmore', 'announcements'], queryFn: safeListAnnouncements });
  const [feedback, setFeedback] = useState('');
  const markRead = useMutation({
    mutationFn: (messageId: string) => markMessageRead(messageId),
    onSuccess: () => client.invalidateQueries({ queryKey: ['hmore', 'inbox'] }),
  });

  async function openMessage(messageId: string, already: StaffAlertInput) {
    setFeedback('');
    try {
      if (!already.read_at) await markRead.mutateAsync(messageId);
      const detail = await getMessage(messageId);
      const href = staffAlertHref({
        related_resource_type: already.related_resource_type ?? null,
        related_resource_id: already.related_resource_id ?? null,
        subject: detail.subject,
        body: detail.body,
      });
      if (href) {
        router.push(href as never);
        return;
      }
      setFeedback(detail.body || 'This alert has no linked record.');
    } catch (error) {
      setFeedback(hmoreErrorMessage(error, 'Could not open this alert.'));
    }
  }

  const messages = inbox.data?.items ?? [];
  return (
    <StaffPage
      title="Notifications"
      subtitle="In-app alerts from communications. This build does not register a device push token. Push end to end is F4.3."
      onRefresh={() => {
        inbox.refetch();
        announcements.refetch();
      }}
      refreshing={inbox.isRefetching || announcements.isRefetching}
    >
      {messages.length === 0 && (announcements.data ?? []).length === 0 ? (
        <Feedback text="The inbox is empty." />
      ) : null}
      {messages.map((message) => (
        <StatusRow
          key={message.recipient_id}
          name={message.subject || 'Message'}
          title={message.subject || 'Message'}
          subtitle={message.body_preview}
          chip={message.read_at ? 'Read' : 'New'}
          tone={message.read_at ? 'gray' : 'blue'}
          onPress={() => openMessage(message.message_id, message)}
        />
      ))}
      {(announcements.data ?? []).map((item) => (
        <StatusRow
          key={item.id}
          name={item.title}
          title={item.title}
          subtitle={item.reference_number}
          chip={item.priority ? staffLabel(item.priority) : undefined}
          tone={statusTone(item.priority)}
        />
      ))}
      {inbox.isError ? <Feedback text={hmoreErrorMessage(inbox.error, 'Could not load alerts.')} /> : null}
      {feedback ? <Feedback text={feedback} /> : null}
    </StaffPage>
  );
}

interface StaffAlertInput {
  read_at: string | null;
  related_resource_type?: string | null;
  related_resource_id?: string | null;
}
