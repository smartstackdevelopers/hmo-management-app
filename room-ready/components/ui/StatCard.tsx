import { Platform, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { webShadow } from '@/constants/fonts';
import { theme } from '@/constants/theme';

type StatVariant = 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';

interface StatCardProps {
  label: string;
  value: string;
  icon?: keyof typeof Ionicons.glyphMap;
  variant?: StatVariant;
  style?: ViewStyle;
}

const variantStyles: Record<StatVariant, { bg: string; icon: string; value: string; border: string }> = {
  default: { bg: theme.colors.surface, icon: theme.colors.textMuted, value: theme.colors.primary, border: theme.colors.borderLight },
  primary: { bg: theme.colors.surface, icon: theme.colors.secondary, value: theme.colors.primary, border: theme.colors.borderLight },
  success: { bg: theme.colors.successLight, icon: theme.colors.success, value: theme.colors.success, border: 'transparent' },
  warning: { bg: theme.colors.warningLight, icon: theme.colors.warning, value: theme.colors.warning, border: 'transparent' },
  error: { bg: theme.colors.errorLight, icon: theme.colors.error, value: theme.colors.error, border: 'transparent' },
  info: { bg: theme.colors.infoLight, icon: theme.colors.info, value: theme.colors.info, border: 'transparent' },
};

export function StatCard({ label, value, icon, variant = 'default', style }: StatCardProps) {
  const colors = variantStyles[variant];

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.bg, borderColor: colors.border },
        Platform.OS === 'web' ? webShadow('sm') : theme.shadows.sm,
        style,
      ]}
    >
      <View style={styles.top}>
        {icon && (
          <View style={styles.iconWrap}>
            <Ionicons name={icon} size={16} color={colors.icon} />
          </View>
        )}
      </View>
      <Text style={[styles.value, { color: colors.value }]} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: theme.radius.lg,
    padding: theme.spacing.md,
    borderWidth: 1,
    minHeight: 96,
    justifyContent: 'space-between',
  },
  top: { flexDirection: 'row', justifyContent: 'flex-start', marginBottom: 8 },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: theme.radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.surfaceSecondary,
  },
  value: {
    fontSize: 24,
    fontWeight: '800',
    letterSpacing: -0.8,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
});
