import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { theme } from '@/constants/theme';

const METRICS = [
  { icon: 'shield-checkmark' as const, value: 'BCC', label: 'Standards aligned' },
  { icon: 'people' as const, value: '5', label: 'User roles' },
  { icon: 'document-text' as const, value: '8+', label: 'Compliance docs' },
];

interface TrustMetricsProps {
  light?: boolean;
}

export function TrustMetrics({ light }: TrustMetricsProps) {
  return (
    <View style={styles.row}>
      {METRICS.map((m) => (
        <View key={m.label} style={[styles.item, light && styles.itemLight]}>
          <Ionicons name={m.icon} size={18} color={light ? theme.colors.accentLight : theme.colors.secondary} />
          <Text style={[styles.value, light && styles.valueLight]}>{m.value}</Text>
          <Text style={[styles.label, light && styles.labelLight]}>{m.label}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    marginVertical: theme.spacing.lg,
  },
  item: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.sm,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
  },
  itemLight: {
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderColor: 'rgba(255,255,255,0.12)',
  },
  value: {
    fontSize: 18,
    fontWeight: '800',
    color: theme.colors.primary,
    marginTop: 6,
    letterSpacing: -0.5,
  },
  valueLight: { color: theme.colors.textInverse },
  label: {
    fontSize: 10,
    fontWeight: '600',
    color: theme.colors.textMuted,
    textAlign: 'center',
    marginTop: 2,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  labelLight: { color: 'rgba(255,255,255,0.65)' },
});
