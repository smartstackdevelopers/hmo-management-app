import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { InitialsTile } from '@/components/dashboard/mobileChrome';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { EmptyState } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { HmoreApiError, hmoreErrorMessage } from '@/lib/hmore/client';
import { getAnnouncement, listAnnouncements, listInbox, markMessageRead } from '@/lib/hmore/services/communications';
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

export function HmoreNotifications() {
  const client = useQueryClient();
  const inbox = useQuery({ queryKey: ['hmore', 'inbox'], queryFn: safeListInbox });
  const announcements = useQuery({ queryKey: ['hmore', 'announcements'], queryFn: safeListAnnouncements });
  const [openBody, setOpenBody] = useState<string | null>(null);
  const [detailError, setDetailError] = useState('');

  const markRead = useMutation({
    mutationFn: (messageId: string) => markMessageRead(messageId),
    onSuccess: () => client.invalidateQueries({ queryKey: ['hmore', 'inbox'] }),
  });

  const refreshing = inbox.isRefetching || announcements.isRefetching;
  const messages = inbox.data?.items ?? [];
  const notices = announcements.data ?? [];
  const unread = messages.filter((item) => !item.read_at).length;

  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            inbox.refetch();
            announcements.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Text style={styles.lead}>
        {unread > 0 ? `${unread} unread message${unread === 1 ? '' : 's'}` : 'Messages and organisation announcements'}
      </Text>
      {inbox.error ? <Text style={styles.error}>{hmoreErrorMessage(inbox.error, 'Could not load messages')}</Text> : null}
      {announcements.error ? <Text style={styles.error}>{hmoreErrorMessage(announcements.error, 'Could not load announcements')}</Text> : null}
      {detailError ? <Text style={styles.error}>{detailError}</Text> : null}

      {notices.map((item) => (
        <Card
          key={item.id}
          style={styles.card}
          onPress={async () => {
            setDetailError('');
            try {
              const detail = await getAnnouncement(item.id);
              setOpenBody(`${detail.title}\n\n${detail.body}`);
            } catch (error) {
              setDetailError(hmoreErrorMessage(error, 'Could not open the announcement'));
            }
          }}
        >
          <View style={styles.row}>
            <InitialsTile name={item.title} size={40} />
            <View style={styles.copy}>
              <Text style={styles.title} numberOfLines={1}>{item.title}</Text>
              <Text style={styles.meta}>Announcement{item.published_at ? ` · ${formatUKDate(item.published_at)}` : ''}</Text>
            </View>
            <Chip label="Notice" tone="indigo" />
          </View>
        </Card>
      ))}

      {messages.map((item) => (
        <Card
          key={item.recipient_id}
          style={[styles.card, !item.read_at && styles.unread]}
          onPress={() => {
            if (!item.read_at) markRead.mutate(item.message_id);
            setOpenBody(`${item.subject}\n\n${item.body_preview}`);
          }}
        >
          <View style={styles.row}>
            <InitialsTile name={item.subject} size={40} />
            <View style={styles.copy}>
              <Text style={styles.title} numberOfLines={1}>{item.subject}</Text>
              <Text style={styles.body} numberOfLines={2}>{item.body_preview}</Text>
            </View>
            {!item.read_at ? <Chip label="New" tone="blue" /> : null}
          </View>
        </Card>
      ))}

      {openBody ? (
        <Card>
          <Text style={styles.body}>{openBody}</Text>
        </Card>
      ) : null}

      {!inbox.isLoading && !announcements.isLoading && notices.length === 0 && messages.length === 0 && !inbox.error ? (
        <EmptyState title="No alerts" message="Messages and announcements from your organisation will appear here." icon="notifications-outline" />
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 40 },
  lead: { fontFamily: FONT_MEDIUM, fontSize: 14, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  error: { color: theme.colors.error, fontFamily: FONT_MEDIUM, marginBottom: 8 },
  card: { marginBottom: theme.spacing.sm },
  unread: { borderColor: theme.colors.secondary, borderWidth: 1 },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, alignItems: 'center' },
  copy: { flex: 1, minWidth: 0 },
  title: { fontFamily: FONT_BOLD, fontSize: 15, color: theme.colors.text },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary, marginTop: 6 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
});
