import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getAnnouncement, listAnnouncements, listInbox, markMessageRead } from '@/lib/hmore/services/communications';

export function HmoreNotifications() {
  const client = useQueryClient();
  const inbox = useQuery({ queryKey: ['hmore', 'inbox'], queryFn: listInbox });
  const announcements = useQuery({ queryKey: ['hmore', 'announcements'], queryFn: listAnnouncements });
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
            <Text style={styles.title}>{item.title}</Text>
            <Badge label={item.priority} format={false} />
          </View>
          <Text style={styles.meta}>Announcement{item.published_at ? ` · ${formatUKDate(item.published_at)}` : ''}</Text>
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
          <Text style={styles.title}>{item.subject}</Text>
          <Text style={styles.body}>{item.body_preview}</Text>
          <Text style={styles.meta}>{formatUKDate(item.created_at)}{item.read_at ? '' : ' · Unread'}</Text>
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
  title: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text, flex: 1 },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary, marginTop: 6 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
});
