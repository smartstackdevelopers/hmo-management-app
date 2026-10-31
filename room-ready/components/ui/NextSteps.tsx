import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { SIMPLE } from '@/constants/simpleCopy';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { formatUKDate } from '@/constants/uk';

export interface TodoItem {
  id: string;
  title: string;
  subtitle: string;
  icon: keyof typeof Ionicons.glyphMap;
  urgent?: boolean;
  onPress: () => void;
}

export function NextSteps({ items, showClear = true }: { items: TodoItem[]; showClear?: boolean }) {
  const shown = items.slice(0, 4);
  const urgentCount = shown.filter((i) => i.urgent).length;

  if (!shown.length && showClear) {
    return (
      <View style={styles.clearCard}>
        <View style={styles.clearIcon}>
          <Ionicons name="checkmark-circle" size={30} color={theme.colors.success} />
        </View>
        <Text style={styles.clearTitle}>All clear</Text>
        <Text style={styles.clearText}>{SIMPLE.home.allCaughtUp}</Text>
      </View>
    );
  }
  if (!shown.length) return null;

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={styles.heading}>{SIMPLE.home.todo}</Text>
        {urgentCount > 0 && (
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{urgentCount} urgent</Text>
          </View>
        )}
      </View>
      <View style={styles.list}>
        {shown.map((item, i) => (
          <Pressable
            key={item.id}
            onPress={item.onPress}
            style={({ pressed }) => [
              styles.row,
              item.urgent && styles.rowUrgent,
              i < shown.length - 1 && styles.border,
              pressed && styles.pressed,
            ]}
          >
            {item.urgent && <View style={styles.urgentBar} />}
            <View style={[styles.icon, item.urgent ? styles.iconUrgent : styles.iconNormal]}>
              <Ionicons
                name={item.icon}
                size={18}
                color={item.urgent ? theme.colors.error : theme.colors.secondary}
              />
            </View>
            <View style={styles.copy}>
              <Text style={styles.title} numberOfLines={1}>{item.title}</Text>
              <Text style={styles.sub} numberOfLines={1}>{item.subtitle}</Text>
            </View>
            <Ionicons name="chevron-forward" size={16} color={theme.colors.textMuted} />
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export function buildDashboardTodos(input: {
  role: string;
  expiringDocuments: { id: string; name: string; expiryDate?: string | null; property?: { id?: string; name?: string } }[];
  openMaintenance: number;
  expiringDocsCount: number;
  hasTenancy: boolean;
  inspectionsDue: number;
  pendingApplications: number;
  propertiesCount: number;
  criticalGaps: number;
  portfolioScore: number | null;
}): TodoItem[] {
  const items: TodoItem[] = [];

  for (const doc of input.expiringDocuments.slice(0, 2)) {
    items.push({
      id: `doc-${doc.id}`,
      title: `Renew ${doc.name}`,
      subtitle: `${doc.property?.name ?? 'Property'} · ${doc.expiryDate ? formatUKDate(doc.expiryDate) : 'soon'}`,
      icon: 'document-text-outline',
      urgent: true,
      onPress: () => {
        const propId = doc.property?.id;
        if (propId) router.push(`/(app)/property/${propId}`);
        else router.push('/(app)/documents');
      },
    });
  }

  if (input.role === 'landlord' || input.role === 'property_manager') {
    if (input.propertiesCount === 0) {
      items.push({
        id: 'add-property',
        title: 'Add your first property',
        subtitle: 'Takes about 2 minutes',
        icon: 'business-outline',
        urgent: true,
        onPress: () => router.push('/(app)/property/new'),
      });
    } else if (input.criticalGaps > 0) {
      items.push({
        id: 'fix-compliance',
        title: 'Fix property checks',
        subtitle: `${input.criticalGaps} missing certificate${input.criticalGaps === 1 ? '' : 's'}`,
        icon: 'shield-checkmark-outline',
        urgent: true,
        onPress: () => router.push('/(app)/(tabs)/compliance'),
      });
    }
    if (input.openMaintenance > 0) {
      items.push({
        id: 'repairs',
        title: 'Open repairs',
        subtitle: `${input.openMaintenance} waiting`,
        icon: 'construct-outline',
        onPress: () => router.push('/(app)/(tabs)/maintenance'),
      });
    }
    if (input.inspectionsDue > 0) {
      items.push({
        id: 'inspections',
        title: 'Inspections due',
        subtitle: `${input.inspectionsDue} to schedule`,
        icon: 'clipboard-outline',
        urgent: true,
        onPress: () => router.push('/(app)/inspection/new'),
      });
    }
  }

  if (input.role === 'tenant') {
    if (!input.hasTenancy) {
      items.push({
        id: 'find-room',
        title: 'Find a room',
        subtitle: 'Search rooms near you',
        icon: 'search-outline',
        onPress: () => router.push('/(app)/(tabs)/find' as never),
      });
    }
    if (input.pendingApplications > 0) {
      items.push({
        id: 'applications',
        title: 'Application updates',
        subtitle: `${input.pendingApplications} pending`,
        icon: 'time-outline',
        onPress: () => router.push('/(app)/(tabs)/tenancy'),
      });
    }
    if (input.openMaintenance > 0) {
      items.push({
        id: 'tenant-repairs',
        title: 'Your repair requests',
        subtitle: `${input.openMaintenance} open`,
        icon: 'construct-outline',
        onPress: () => router.push('/(app)/(tabs)/maintenance'),
      });
    }
  }

  return items;
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.lg },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.sm,
  },
  heading: {
    fontSize: 17,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.2,
  },
  countBadge: {
    backgroundColor: theme.colors.errorLight,
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: theme.radius.full,
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  countText: { fontSize: 11, fontFamily: FONT_SEMIBOLD, fontWeight: '700', color: theme.colors.error },
  list: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 14,
    paddingHorizontal: theme.spacing.md,
    position: 'relative',
  },
  rowUrgent: { backgroundColor: '#FFFBFB' },
  border: { borderBottomWidth: 1, borderBottomColor: theme.colors.borderLight },
  pressed: { backgroundColor: theme.colors.surfaceMuted },
  urgentBar: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 3,
    backgroundColor: theme.colors.error,
  },
  icon: {
    width: 38,
    height: 38,
    borderRadius: theme.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconUrgent: { backgroundColor: theme.colors.errorLight },
  iconNormal: { backgroundColor: theme.colors.accentLight },
  copy: { flex: 1, minWidth: 0 },
  title: { fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  sub: { fontSize: 13, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 },
  clearCard: {
    alignItems: 'center',
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  clearIcon: { marginBottom: theme.spacing.sm },
  clearTitle: { fontSize: 17, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text },
  clearText: {
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    marginTop: 4,
    lineHeight: 20,
  },
});
