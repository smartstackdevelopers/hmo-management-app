import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';

import { Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { staffAlertHref } from '@/lib/hmore/staff/alerts';
import { getMessage, listAnnouncements, listInbox, markMessageRead } from '@/lib/hmore/services/communications';

export function StaffAlertList() {
  const client = useQueryClient();
  const inbox = useQuery({ queryKey: ['hmore', 'inbox'], queryFn: listInbox });
  const announcements = useQuery({ queryKey: ['hmore', 'announcements'], queryFn: listAnnouncements });
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
        <RecordCard title="No alerts" detail="The inbox is empty." />
      ) : null}
      {messages.map((message) => (
        <RecordCard
          key={message.recipient_id}
          title={message.subject || 'Message'}
          status={message.read_at ? 'read' : 'new'}
          detail={message.body_preview}
          onPress={() => openMessage(message.message_id, message)}
        />
      ))}
      {(announcements.data ?? []).map((item) => (
        <RecordCard key={item.id} title={item.title} status={item.priority} detail={item.reference_number} />
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
