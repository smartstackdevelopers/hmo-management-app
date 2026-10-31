import { StyleSheet, Text, View } from 'react-native';

import { FONT_SEMIBOLD } from '@/constants/fonts';
import { formatLabel } from '@/lib/format';
import { theme } from '@/constants/theme';

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info';

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  format?: boolean;
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; border: string }> = {
  default: { bg: theme.colors.surfaceMuted, text: theme.colors.textSecondary, border: theme.colors.border },
  success: { bg: theme.colors.successLight, text: theme.colors.success, border: '#A7F3D0' },
  warning: { bg: theme.colors.warningLight, text: theme.colors.warning, border: '#FDE68A' },
  error: { bg: theme.colors.errorLight, text: theme.colors.error, border: '#FECACA' },
  info: { bg: theme.colors.accentLight, text: theme.colors.secondaryDark, border: '#99F6E4' },
};

export function Badge({ label, variant = 'default', format = true }: BadgeProps) {
  const colors = variantStyles[variant];
  const text = format ? formatLabel(label) : label;

  return (
    <View style={[styles.badge, { backgroundColor: colors.bg, borderColor: colors.border }]}>
      <Text style={[styles.text, { color: colors.text }]} numberOfLines={1}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: theme.radius.full,
    alignSelf: 'flex-start',
    borderWidth: 1,
  },
  text: {
    fontSize: 11,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    letterSpacing: 0.1,
  },
});
