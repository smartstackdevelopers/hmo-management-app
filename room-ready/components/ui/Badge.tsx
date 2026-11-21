import { StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { toneColors, type Tone } from '@/components/ui/Chip';
import { FONT_SEMIBOLD } from '@/constants/fonts';
import { formatLabel } from '@/lib/format';
import { theme } from '@/constants/theme';

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info' | 'primary' | 'neutral';

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  format?: boolean;
  /** Overrides `variant` with a status tone (green/amber/red/blue/indigo/gray/navy). */
  tone?: Tone;
  dot?: boolean;
  style?: StyleProp<ViewStyle>;
}

const variantTone: Record<BadgeVariant, Tone> = {
  default: 'gray',
  neutral: 'gray',
  success: 'green',
  warning: 'amber',
  error: 'red',
  info: 'blue',
  primary: 'blue',
};

export function Badge({ label, variant = 'default', format = true, tone, dot = false, style }: BadgeProps) {
  const colors = toneColors[tone ?? variantTone[variant]];
  const text = format ? formatLabel(label) : label;

  return (
    <View style={[styles.badge, { backgroundColor: colors.bg, borderColor: colors.border }, style]}>
      {dot && <View style={[styles.dot, { backgroundColor: colors.text }]} />}
      <Text style={[styles.text, { color: colors.text }]} numberOfLines={1}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radius.full,
    alignSelf: 'flex-start',
    borderWidth: 1,
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  text: {
    fontSize: 11,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    letterSpacing: 0.1,
  },
});
