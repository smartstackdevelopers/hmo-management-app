import { Ionicons } from '@expo/vector-icons';

import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { IconTile } from '@/components/ui/IconTile';
import { Section } from '@/components/ui/Section';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { formatUKDate } from '@/constants/uk';
import { NotificationItem } from '@/lib/api';
import { StyleSheet, Text, View } from 'react-native';

interface NotifItem extends Pick<NotificationItem, 'id' | 'title' | 'body' | 'createdAt' | 'read' | 'type' | 'data'> {}

interface ActivityFeedProps {
  notifications: NotifItem[];
  onSeeAllNotifications: () => void;
  onNotificationPress: (notification: NotificationItem) => void;
  title?: string;
}

const ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  maintenance: 'construct-outline',
  application: 'document-text-outline',
  message: 'chatbubble-outline',
  compliance: 'shield-checkmark-outline',
  inspection: 'clipboard-outline',
};

export function ActivityFeed({
  notifications,
  onSeeAllNotifications,
  onNotificationPress,
  title = 'Recent updates',
}: ActivityFeedProps) {
  if (notifications.length === 0) return null;

  return (
    <Section title={title} actionLabel="See all" onAction={onSeeAllNotifications}>
      <View style={styles.list}>
        {notifications.slice(0, 4).map((item) => (
          <Card key={item.id} onPress={() => onNotificationPress(item)} style={styles.card}>
            <View style={styles.row}>
              <IconTile icon={ICONS[item.type] ?? 'notifications-outline'} tone={item.read ? 'gray' : 'blue'} size={40} />
              <View style={styles.copy}>
                <Text style={styles.title} numberOfLines={1}>{item.title}</Text>
                <Text style={styles.subtitle} numberOfLines={2}>
                  {item.body} · {formatUKDate(item.createdAt)}
                </Text>
              </View>
              {!item.read ? <Chip label="New" tone="blue" /> : null}
            </View>
          </Card>
        ))}
      </View>
    </Section>
  );
}

const styles = StyleSheet.create({
  list: { gap: theme.spacing.sm },
  card: { marginBottom: 0 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  subtitle: { fontSize: 13, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 },
});
