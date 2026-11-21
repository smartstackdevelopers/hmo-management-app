import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, StyleSheet, Text, View } from 'react-native';

import { FilterChips, InitialsTile, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useConversations } from '@/hooks/useApi';
import { ConversationItem } from '@/lib/api';
import { HmoreApiError } from '@/lib/hmore/client';
import { getAnnouncement, listAnnouncements, listInbox } from '@/lib/hmore/services/communications';
import type { AnnouncementSummary } from '@/lib/hmore/types';

type InboxFilter = 'all' | 'unread' | 'announcements';

async function loadAnnouncements(): Promise<AnnouncementSummary[]> {
  try {
    return await listAnnouncements();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 400 || error.status === 403 || error.status === 404)) {
      return [];
    }
    throw error;
  }
}

export default function MessagesScreen() {
  useHideTabHeader();
  const { hmore } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useConversations();
  const inbox = useQuery({
    queryKey: ['hmore', 'inbox', 'messages-tab'],
    queryFn: listInbox,
    enabled: !!hmore,
  });
  const announcements = useQuery({
    queryKey: ['hmore', 'announcements', 'messages-tab'],
    queryFn: loadAnnouncements,
    enabled: !!hmore,
  });
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<InboxFilter>('all');

  const conversations = data?.conversations ?? [];
  const unreadIds = useMemo(() => {
    const ids = new Set<string>();
    for (const item of inbox.data?.items ?? []) {
      if (item.read_at) continue;
      if (item.conversation_id) ids.add(item.conversation_id);
      if (item.message_id) ids.add(item.message_id);
    }
    return ids;
  }, [inbox.data]);
  const canFilterUnread = !!hmore && inbox.isSuccess;
  const noticeRows = announcements.data ?? [];
  const showAnnouncements = !!hmore && announcements.isSuccess;

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return conversations.filter((item) => {
      if (filter === 'announcements') return false;
      if (filter === 'unread' && canFilterUnread && !unreadIds.has(item.id)) return false;
      if (!needle) return true;
      const other = item.participants.find((participant) => participant.user)?.user;
      const name = other ? `${other.firstName} ${other.lastName}` : '';
      const preview = item.messages[0]?.body ?? '';
      return `${item.subject ?? ''} ${item.property?.name ?? ''} ${name} ${preview}`.toLowerCase().includes(needle);
    });
  }, [conversations, filter, query, canFilterUnread, unreadIds]);

  const filteredNotices = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return noticeRows;
    return noticeRows.filter((item) => `${item.title} ${item.reference_number}`.toLowerCase().includes(needle));
  }, [noticeRows, query]);

  const chips = [
    { id: 'all', label: 'All' },
    ...(canFilterUnread ? [{ id: 'unread', label: 'Unread' }] : []),
    ...(showAnnouncements ? [{ id: 'announcements', label: 'Announcements' }] : []),
  ];

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load messages" onRetry={refetch} />;

  const showingNotices = filter === 'announcements';
  const listEmpty = showingNotices ? filteredNotices.length === 0 : filtered.length === 0;
  const sourceEmpty = conversations.length === 0 && noticeRows.length === 0;

  return showingNotices ? (
    <ListScreen
      data={filteredNotices}
      keyExtractor={(item) => item.id}
      refreshing={isRefetching || announcements.isRefetching}
      onRefresh={() => {
        refetch();
        announcements.refetch();
      }}
      contentContainerStyle={listEmpty ? styles.emptyList : undefined}
      ListHeaderComponent={
        <MessageHeader
          count={conversations.length}
          query={query}
          onQuery={setQuery}
          chips={chips}
          filter={filter}
          onFilter={setFilter}
        />
      }
      ListEmptyComponent={
        <EmptyState
          title={sourceEmpty ? 'No conversations' : 'No announcements'}
          message={sourceEmpty ? 'Messages appear here when a conversation starts.' : 'Published notices will show up here.'}
          icon="chatbubbles-outline"
          actionLabel={sourceEmpty ? 'New message' : undefined}
          onAction={sourceEmpty ? () => router.push('/(app)/conversation/new') : undefined}
        />
      }
      renderItem={({ item }) => <AnnouncementRow item={item} />}
    />
  ) : (
    <ListScreen
      data={filtered}
      keyExtractor={(item) => item.id}
      refreshing={isRefetching || inbox.isRefetching}
      onRefresh={() => {
        refetch();
        if (hmore) inbox.refetch();
      }}
      contentContainerStyle={listEmpty ? styles.emptyList : undefined}
      ListHeaderComponent={
        <MessageHeader
          count={conversations.length}
          query={query}
          onQuery={setQuery}
          chips={chips}
          filter={filter}
          onFilter={setFilter}
        />
      }
      ListEmptyComponent={
        <EmptyState
          title={conversations.length === 0 ? 'No conversations' : 'Nothing in this filter'}
          message={
            conversations.length === 0
              ? 'Messages appear here when a conversation starts.'
              : 'Try another filter or search.'
          }
          icon="chatbubbles-outline"
          actionLabel={conversations.length === 0 ? 'New message' : undefined}
          onAction={conversations.length === 0 ? () => router.push('/(app)/conversation/new') : undefined}
        />
      }
      renderItem={({ item }) => <ConversationRow item={item} unread={canFilterUnread && unreadIds.has(item.id)} />}
    />
  );
}

function MessageHeader({
  count,
  query,
  onQuery,
  chips,
  filter,
  onFilter,
}: {
  count: number;
  query: string;
  onQuery: (value: string) => void;
  chips: { id: string; label: string }[];
  filter: InboxFilter;
  onFilter: (id: InboxFilter) => void;
}) {
  return (
    <View>
      <ScreenHeader
        title="Messages"
        subtitle={`${count} conversation${count === 1 ? '' : 's'}`}
        action={<Button title="New" icon="add" size="sm" onPress={() => router.push('/(app)/conversation/new')} />}
      />
      <SearchField value={query} onChangeText={onQuery} placeholder="Search messages" />
      {chips.length > 1 ? <FilterChips options={chips} value={filter} onChange={(id) => onFilter(id as InboxFilter)} /> : null}
    </View>
  );
}

function ConversationRow({ item, unread }: { item: ConversationItem; unread: boolean }) {
  const lastMessage = item.messages[0];
  const other = item.participants.find((participant) => participant.user)?.user;
  const person = other ? `${other.firstName} ${other.lastName}`.trim() : '';
  const displayName = person || item.subject || item.property?.name || 'Conversation';
  const preview = lastMessage?.body || item.subject || 'No messages yet';

  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/conversation/${item.id}`)}>
      <View style={styles.row}>
        <InitialsTile name={person || displayName} size={44} />
        <View style={styles.copy}>
          <Text style={styles.subject} numberOfLines={1}>{displayName}</Text>
          <Text style={styles.preview} numberOfLines={1}>{preview}</Text>
        </View>
        {unread ? <Chip label="New" tone="blue" /> : null}
        <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
      </View>
    </Card>
  );
}

function AnnouncementRow({ item }: { item: AnnouncementSummary }) {
  const meta = [item.reference_number, item.published_at ? formatUKDate(item.published_at) : null].filter(Boolean).join(' · ');
  return (
    <Card
      style={styles.card}
      onPress={() => {
        getAnnouncement(item.id)
          .then((detail) => Alert.alert(detail.title, detail.body || item.reference_number))
          .catch((error: unknown) => Alert.alert('Notice', error instanceof Error ? error.message : 'Could not open this notice'));
      }}
    >
      <View style={styles.row}>
        <InitialsTile name={item.title} size={44} />
        <View style={styles.copy}>
          <Text style={styles.subject} numberOfLines={1}>{item.title}</Text>
          {meta ? <Text style={styles.preview} numberOfLines={1}>{meta}</Text> : null}
        </View>
        <Chip label="Notice" tone={'indigo' satisfies Tone} />
        <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  emptyList: { flexGrow: 1 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  subject: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 15, color: theme.colors.text },
  preview: { color: theme.colors.textSecondary, marginTop: 2, fontSize: 13, fontFamily: FONT_MEDIUM },
});
