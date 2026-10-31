import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { theme } from '@/constants/theme';
import { formatUKDate } from '@/constants/uk';

interface ActivityRowProps {
  icon: keyof typeof Ionicons.glyphMap;
  iconColor: string;
  iconBg: string;
  title: string;
  subtitle: string;
  onPress?: () => void;
  compact?: boolean;
  unread?: boolean;
}

function RowContent({
  icon,
  iconColor,
  iconBg,
  title,
  subtitle,
  onPress,
  compact,
  unread,
}: ActivityRowProps) {
  return (
    <View style={[styles.row, compact && styles.rowCompact]}>
      <View style={[styles.iconWrap, compact && styles.iconWrapCompact, { backgroundColor: iconBg }]}>
        <Ionicons name={icon} size={compact ? 16 : 18} color={iconColor} />
      </View>
      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <Text style={[styles.title, unread && styles.titleUnread]} numberOfLines={1}>{title}</Text>
          {unread && <View style={styles.unreadDot} />}
        </View>
        <Text style={styles.subtitle} numberOfLines={2}>{subtitle}</Text>
      </View>
      {onPress && <Ionicons name="chevron-forward" size={16} color={theme.colors.textMuted} />}
    </View>
  );
}

export function ActivityRow(props: ActivityRowProps) {
  const { onPress, compact } = props;

  if (compact) {
    if (onPress) {
      return (
        <Pressable onPress={onPress} style={({ pressed }) => [styles.compactWrap, pressed && styles.pressed]}>
          <RowContent {...props} />
        </Pressable>
      );
    }
    return (
      <View style={styles.compactWrap}>
        <RowContent {...props} />
      </View>
    );
  }

  return (
    <Card style={styles.card} onPress={onPress}>
      <RowContent {...props} />
    </Card>
  );
}

export function NotificationRow({
  title,
  body,
  createdAt,
  onPress,
  compact,
  unread,
}: {
  title: string;
  body: string;
  createdAt: string;
  onPress?: () => void;
  compact?: boolean;
  unread?: boolean;
}) {
  return (
    <ActivityRow
      icon="notifications-outline"
      iconColor={unread ? theme.colors.secondary : theme.colors.textMuted}
      iconBg={unread ? theme.colors.infoLight : theme.colors.surfaceMuted}
      title={title}
      subtitle={`${body} · ${formatUKDate(createdAt)}`}
      onPress={onPress}
      compact={compact}
      unread={unread}
    />
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.sm, paddingVertical: 12 },
  compactWrap: {
    paddingVertical: 13,
    paddingHorizontal: theme.spacing.md,
  },
  pressed: { backgroundColor: theme.colors.surfaceMuted },
  row: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  rowCompact: { gap: theme.spacing.sm },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: theme.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrapCompact: {
    width: 36,
    height: 36,
    borderRadius: theme.radius.sm,
  },
  copy: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  title: { fontWeight: '600', fontSize: 14, color: theme.colors.text, flex: 1 },
  titleUnread: { fontWeight: '800' },
  unreadDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: theme.colors.secondary,
  },
  subtitle: { fontSize: 13, color: theme.colors.textSecondary, marginTop: 2, lineHeight: 18 },
});
