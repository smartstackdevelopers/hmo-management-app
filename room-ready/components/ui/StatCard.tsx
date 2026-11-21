import { Platform, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD, webShadow } from '@/constants/fonts';
import { theme } from '@/constants/theme';

type StatVariant = 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';

interface StatCardProps {
  label: string;
  value: string;
  icon?: keyof typeof Ionicons.glyphMap;
  variant?: StatVariant;
  style?: ViewStyle;
  /** Quiet line under the label, such as a comparison. */
  hint?: string;
}

const variantStyles: Record<StatVariant, { bg: string; icon: string; value: string; border: string; tile: string }> = {
  default: {
    bg: theme.colors.surface,
    icon: theme.colors.secondaryDark,
    value: theme.colors.text,
    border: theme.colors.border,
    tile: theme.colors.accentLight,
  },
  primary: {
    bg: theme.colors.surface,
    icon: theme.colors.secondaryDark,
    value: theme.colors.text,
    border: theme.colors.border,
    tile: theme.colors.accentLight,
  },
  success: {
    bg: theme.colors.successLight,
    icon: theme.colors.success,
    value: theme.colors.success,
    border: 'transparent',
    tile: theme.colors.surface,
  },
  warning: {
    bg: theme.colors.warningLight,
    icon: theme.colors.warning,
    value: theme.colors.warning,
    border: 'transparent',
    tile: theme.colors.surface,
  },
  error: {
    bg: theme.colors.errorLight,
    icon: theme.colors.error,
    value: theme.colors.error,
    border: 'transparent',
    tile: theme.colors.surface,
  },
  info: {
    bg: theme.colors.infoLight,
    icon: theme.colors.info,
    value: theme.colors.info,
    border: 'transparent',
    tile: theme.colors.surface,
  },
};

export function StatCard({ label, value, icon, variant = 'default', style, hint }: StatCardProps) {
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
      {icon ? (
        <View style={[styles.iconWrap, { backgroundColor: colors.tile }]}>
          <Ionicons name={icon} size={18} color={colors.icon} />
        </View>
      ) : null}
      <Text style={[styles.value, { color: colors.value }]} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      <Text style={styles.label} numberOfLines={2}>
        {label}
      </Text>
      {hint ? (
        <Text style={styles.hint} numberOfLines={1}>
          {hint}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: theme.radius.lg,
    padding: theme.spacing.md,
    borderWidth: 1,
    minHeight: 108,
    justifyContent: 'flex-end',
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  value: {
    fontSize: 26,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    letterSpacing: -0.6,
  },
  label: {
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  hint: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    color: theme.colors.textMuted,
    marginTop: 4,
  },
});
