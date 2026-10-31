import { FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { NotificationItem } from '@/lib/api';
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotifications, useRunComplianceScan } from '@/hooks/useApi';
import { navigateFromNotification } from '@/lib/notificationNavigation';

const TYPE_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  maintenance: 'construct-outline',
  application: 'document-text-outline',
  message: 'chatbubble-outline',
  compliance: 'shield-checkmark-outline',
  inspection: 'clipboard-outline',
};

export default function NotificationsScreen() {
  const { data, isLoading, error, refetch, isRefetching } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();
  const runScan = useRunComplianceScan();

  if (isLoading) return <LoadingScreen message="Loading notifications..." />;
  if (error) return <ErrorState message="Could not load notifications" onRetry={refetch} />;

  const notifications = data?.notifications ?? [];
  const unreadCount = data?.unreadCount ?? 0;

  function handlePress(n: NotificationItem) {
    if (!n.read) markRead.mutate(n.id);
    navigateFromNotification(n);
  }

  return (
    <View style={styles.container}>
      {unreadCount > 0 && (
        <View style={styles.header}>
          <Text style={styles.unread}>{unreadCount} unread</Text>
          <View style={styles.headerActions}>
            <Button title="AI scan" variant="outline" size="sm" onPress={() => runScan.mutate()} loading={runScan.isPending} />
            <Button title="Mark all read" variant="outline" size="sm" onPress={() => markAll.mutate()} />
          </View>
        </View>
      )}
      <FlatList
        data={notifications}
        keyExtractor={(item) => item.id}
        style={styles.list}
        contentContainerStyle={notifications.length === 0 ? styles.emptyList : styles.listContent}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}
        ListEmptyComponent={
          <EmptyState
            title="No notifications"
            message="Alerts about repairs, applications and compliance will appear here."
            icon="notifications-outline"
          />
        }
        renderItem={({ item }) => (
          <NotificationCard item={item} onPress={() => handlePress(item)} />
        )}
      />
    </View>
  );
}

function NotificationCard({ item, onPress }: { item: NotificationItem; onPress: () => void }) {
  const icon = TYPE_ICONS[item.type] ?? 'notifications-outline';
  return (
    <Card style={!item.read ? [styles.card, styles.unreadCard] : styles.card} onPress={onPress}>
      <View style={styles.row}>
        <View style={[styles.iconWrap, !item.read && styles.iconWrapUnread]}>
          <Ionicons name={icon} size={18} color={theme.colors.secondary} />
        </View>
        <View style={styles.copy}>
          <View style={styles.titleRow}>
            <Text style={styles.title} numberOfLines={1}>{item.title}</Text>
            {item.severity && item.severity !== 'info' ? (
              <Badge
                label={item.severity === 'critical' ? 'Critical' : item.severity === 'high' ? 'High' : 'Medium'}
                variant={item.severity === 'critical' ? 'error' : item.severity === 'high' ? 'warning' : 'info'}
              />
            ) : null}
            {!item.read && <Badge label="New" variant="info" />}
          </View>
          <Text style={styles.body} numberOfLines={2}>{item.body}</Text>
          <Text style={styles.date}>{formatUKDate(item.createdAt)}</Text>
        </View>
        <Ionicons name="chevron-forward" size={16} color={theme.colors.textMuted} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: theme.spacing.md, paddingBottom: 0 },
  headerActions: { flexDirection: 'row', gap: 8 },
  unread: { fontWeight: '600', color: theme.colors.secondary },
  list: { flex: 1 },
  listContent: { padding: theme.spacing.md, paddingBottom: theme.spacing.xl },
  emptyList: { flex: 1 },
  card: { marginBottom: theme.spacing.sm, paddingVertical: 12 },
  unreadCard: { borderColor: theme.colors.info, backgroundColor: theme.colors.infoLight },
  row: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.surfaceSecondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrapUnread: { backgroundColor: theme.colors.surface },
  copy: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  title: { fontWeight: '600', fontSize: 15, color: theme.colors.text, flex: 1 },
  body: { color: theme.colors.textSecondary, marginTop: 4, lineHeight: 20, fontSize: 14 },
  date: { color: theme.colors.textMuted, fontSize: 12, marginTop: 6 },
});
