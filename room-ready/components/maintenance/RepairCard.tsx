import { router } from 'expo-router';
import { Image, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { MaintenanceItem } from '@/lib/api';
import { getFileUrl } from '@/lib/config';
import {
  PRIORITY_COLOR,
  PRIORITY_VARIANT,
  STATUS_VARIANT,
  categoryIcon,
  isUrgentPriority,
  relativeTime,
  statusLabel,
} from '@/lib/maintenance';

export function RepairCard({ item }: { item: MaintenanceItem }) {
  const accent = PRIORITY_COLOR[item.priority] ?? theme.colors.border;
  const icon = categoryIcon(item.category);
  const thumb = item.photoUrls?.[0];
  const urgent = isUrgentPriority(item.priority);

  return (
    <Card
      style={[styles.card, urgent && styles.cardUrgent]}
      onPress={() => router.push(`/(app)/maintenance/${item.id}`)}
    >
      <View style={styles.top}>
        {thumb ? (
          <Image source={{ uri: getFileUrl(thumb) }} style={styles.thumb} />
        ) : (
          <View style={[styles.iconTile, { backgroundColor: `${accent}18` }]}>
            <Ionicons name={icon} size={20} color={accent} />
          </View>
        )}
        <View style={styles.copy}>
          <View style={styles.titleRow}>
            <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
            <Ionicons name="chevron-forward" size={16} color={theme.colors.textMuted} />
          </View>
          <Text style={styles.property} numberOfLines={1}>
            {item.property?.name}
            {item.room ? ` · ${item.room.name}` : ''}
          </Text>
          <View style={styles.meta}>
            <Badge label={statusLabel(item.status)} variant={STATUS_VARIANT[item.status] ?? 'default'} format={false} />
            <Badge
              label={item.priority === 'emergency' ? 'Emergency' : item.priority}
              variant={PRIORITY_VARIANT[item.priority] ?? 'default'}
            />
          </View>
        </View>
      </View>

      <View style={styles.footer}>
        <View style={styles.footerLeft}>
          <Ionicons name={icon} size={13} color={theme.colors.textMuted} />
          <Text style={styles.category}>{item.category}</Text>
        </View>
        <Text style={styles.date}>{relativeTime(item.createdAt)}</Text>
      </View>

      {item.contractor && (
        <View style={styles.contractorRow}>
          <Ionicons name="person-outline" size={13} color={theme.colors.secondary} />
          <Text style={styles.contractor}>
            {item.contractor.firstName} {item.contractor.lastName}
          </Text>
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.sm },
  cardUrgent: {
    borderColor: theme.colors.error,
    backgroundColor: theme.colors.errorLight,
  },
  top: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  thumb: {
    width: 56,
    height: 56,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.surfaceMuted,
  },
  iconTile: {
    width: 56,
    height: 56,
    borderRadius: theme.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: { flex: 1, minWidth: 0 },
  titleRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 6 },
  title: {
    flex: 1,
    fontSize: 15,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.2,
    lineHeight: 20,
  },
  property: {
    color: theme.colors.textSecondary,
    marginTop: 4,
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
  },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8, flexWrap: 'wrap' },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderLight,
  },
  footerLeft: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  category: {
    color: theme.colors.textMuted,
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
  },
  date: { color: theme.colors.textMuted, fontSize: 12, fontFamily: FONT_MEDIUM },
  contractorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginTop: 8,
  },
  contractor: {
    color: theme.colors.secondary,
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
  },
});
