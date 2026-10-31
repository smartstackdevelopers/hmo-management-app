import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Avatar } from '@/components/ui/ListRow';
import { Card } from '@/components/ui/Card';
import { ListScreen } from '@/components/ui/ListScreen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useFabBottom } from '@/hooks/useLayout';
import { ConversationItem } from '@/lib/api';
import { useConversations } from '@/hooks/useApi';

export default function MessagesScreen() {
  const { data, isLoading, error, refetch, isRefetching } = useConversations();
  const fabBottom = useFabBottom();

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load messages" onRetry={refetch} />;

  const conversations = data?.conversations ?? [];

  return (
    <View style={styles.container}>
      <ListScreen
        data={conversations}
        keyExtractor={(item) => item.id}
        refreshing={isRefetching}
        onRefresh={refetch}
        fabClearance={conversations.length > 0 ? theme.layout.fabSize + theme.spacing.md : 0}
        contentContainerStyle={conversations.length === 0 ? styles.emptyList : undefined}
        ListEmptyComponent={
          <EmptyState
            title="No conversations"
            message="Messages with landlords, tenants and contractors appear here."
            icon="chatbubbles-outline"
            actionLabel="New message"
            onAction={() => router.push('/(app)/conversation/new')}
          />
        }
        renderItem={({ item }) => <ConversationCard item={item} />}
      />

      {conversations.length > 0 && (
        <Pressable
          style={[styles.fab, { bottom: fabBottom }]}
          onPress={() => router.push('/(app)/conversation/new')}
        >
          <Ionicons name="create-outline" size={22} color={theme.colors.textInverse} />
        </Pressable>
      )}
    </View>
  );
}

function ConversationCard({ item }: { item: ConversationItem }) {
  const lastMessage = item.messages[0];
  const other = item.participants.find((p) => p.user)?.user;
  const displayName = item.subject ?? item.property?.name ?? other?.firstName ?? 'Conversation';
  const preview = lastMessage
    ? `${lastMessage.sender?.firstName ?? 'Someone'}: ${lastMessage.body}`
    : 'No messages yet';

  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/conversation/${item.id}`)}>
      <View style={styles.row}>
        <Avatar name={other ? `${other.firstName} ${other.lastName}` : displayName} size={46} />
        <View style={styles.copy}>
          <View style={styles.titleRow}>
            <Text style={styles.subject} numberOfLines={1}>
              {displayName}
            </Text>
            <Text style={styles.date}>{formatUKDate(item.updatedAt)}</Text>
          </View>
          <Text style={styles.preview} numberOfLines={2}>
            {preview}
          </Text>
        </View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  emptyList: { flexGrow: 1 },
  card: { marginBottom: theme.spacing.sm, paddingVertical: 12 },
  row: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  copy: { flex: 1, minWidth: 0 },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  subject: { fontWeight: '700', fontSize: 15, color: theme.colors.text, flex: 1, minWidth: 0 },
  date: { color: theme.colors.textMuted, fontSize: 11, fontWeight: '600', flexShrink: 0 },
  preview: { color: theme.colors.textSecondary, marginTop: 4, fontSize: 13, lineHeight: 18 },
  fab: {
    position: 'absolute',
    right: theme.spacing.md,
    width: theme.layout.fabSize,
    height: theme.layout.fabSize,
    borderRadius: theme.layout.fabSize / 2,
    backgroundColor: theme.colors.secondary,
    alignItems: 'center',
    justifyContent: 'center',
    ...theme.shadows.glow,
  },
});
