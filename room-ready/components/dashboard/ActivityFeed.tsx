import { Pressable, StyleSheet, Text, View } from 'react-native';

import { NotificationRow } from '@/components/dashboard/ActivityRow';
import { SIMPLE } from '@/constants/simpleCopy';
import { FONT_BOLD, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { NotificationItem } from '@/lib/api';

interface NotifItem extends Pick<NotificationItem, 'id' | 'title' | 'body' | 'createdAt' | 'read' | 'type' | 'data'> {}

interface ActivityFeedProps {
  notifications: NotifItem[];
  onSeeAllNotifications: () => void;
  onNotificationPress: (notification: NotificationItem) => void;
}

export function ActivityFeed({
  notifications,
  onSeeAllNotifications,
  onNotificationPress,
}: ActivityFeedProps) {
  if (notifications.length === 0) return null;

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={styles.title}>{SIMPLE.home.updates}</Text>
        <Pressable onPress={onSeeAllNotifications} hitSlop={8}>
          <Text style={styles.action}>See all</Text>
        </Pressable>
      </View>
      <View style={styles.list}>
        {notifications.slice(0, 3).map((n, i) => (
          <View key={n.id}>
            {i > 0 && <View style={styles.divider} />}
            <NotificationRow
              title={n.title}
              body={n.body}
              createdAt={n.createdAt}
              unread={!n.read}
              onPress={() => onNotificationPress(n)}
              compact
            />
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.lg },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
  },
  title: {
    fontSize: 17,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.2,
  },
  action: {
    fontSize: 14,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.secondary,
  },
  list: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    overflow: 'hidden',
  },
  divider: {
    height: 1,
    backgroundColor: theme.colors.borderLight,
    marginLeft: 56,
  },
});
