import { StyleSheet, Text, View } from 'react-native';

import { theme } from '@/constants/theme';
import type { DashboardStat } from './DashboardStatsPanel.types';

export type { DashboardStat } from './DashboardStatsPanel.types';

const VARIANT_COLORS = {
  default: theme.colors.text,
  primary: theme.colors.text,
  success: theme.colors.success,
  warning: theme.colors.warning,
  error: theme.colors.error,
  info: theme.colors.info,
} as const;

export function DashboardStatsPanel({ stats }: { stats: DashboardStat[] }) {
  const shown = stats.slice(0, 2);
  if (!shown.length) return null;

  return (
    <View style={styles.row}>
      {shown.map((stat) => {
        const valueColor = VARIANT_COLORS[stat.variant ?? 'default'];
        return (
          <View key={stat.label} style={styles.tile}>
            <Text style={[styles.value, { color: valueColor }]}>{stat.value}</Text>
            <Text style={styles.label}>{stat.label}</Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.lg },
  tile: {
    flex: 1,
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  value: { fontSize: 22, fontWeight: '700', letterSpacing: -0.5 },
  label: { fontSize: 13, color: theme.colors.textSecondary, marginTop: 2 },
});
