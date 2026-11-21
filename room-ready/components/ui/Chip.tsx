import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export type Tone = 'green' | 'amber' | 'red' | 'blue' | 'indigo' | 'gray' | 'navy';

export const toneColors: Record<Tone, { bg: string; text: string; border: string }> = {
  green: { bg: theme.colors.successLight, text: '#047857', border: '#A7F3D0' },
  amber: { bg: theme.colors.warningLight, text: '#B45309', border: '#FDE68A' },
  red: { bg: theme.colors.errorLight, text: '#B91C1C', border: '#FECACA' },
  blue: { bg: theme.colors.accentLight, text: theme.colors.secondaryDark, border: theme.colors.accentSoft },
  indigo: { bg: theme.colors.infoLight, text: theme.colors.info, border: '#C7D2FE' },
  gray: { bg: theme.colors.surfaceMuted, text: theme.colors.textSecondary, border: theme.colors.border },
  navy: { bg: theme.colors.brand, text: theme.colors.textInverse, border: theme.colors.brand },
};

interface ChipProps {
  label: string;
  tone?: Tone;
  icon?: keyof typeof Ionicons.glyphMap;
  dot?: boolean;
  size?: 'sm' | 'md';
  /** Filter-chip mode: when `onPress` is set the chip becomes a toggle. */
  selected?: boolean;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
}

export function Chip({
  label,
  tone = 'gray',
  icon,
  dot = false,
  size = 'sm',
  selected,
  onPress,
  style,
  accessibilityLabel,
}: ChipProps) {
  const filter = !!onPress;
  const colors = filter
    ? selected
      ? { bg: theme.colors.secondaryDark, text: theme.colors.textInverse, border: theme.colors.secondaryDark }
      : { bg: theme.colors.surface, text: theme.colors.textSecondary, border: theme.colors.border }
    : toneColors[tone];

  const body = (
    <>
      {dot && <View style={[styles.dot, { backgroundColor: colors.text }]} />}
      {icon && <Ionicons name={icon} size={size === 'md' ? 14 : 12} color={colors.text} />}
      <Text style={[styles.text, size === 'md' && styles.textMd, { color: colors.text }]} numberOfLines={1}>
        {label}
      </Text>
    </>
  );

  const chipStyle = [
    styles.chip,
    size === 'md' && styles.chipMd,
    filter && styles.filter,
    { backgroundColor: colors.bg, borderColor: colors.border },
    style,
  ];

  if (filter) {
    return (
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel ?? label}
        accessibilityState={{ selected: !!selected }}
        hitSlop={6}
        style={({ pressed }) => [...chipStyle, pressed && styles.pressed]}
      >
        {body}
      </Pressable>
    );
  }

  return (
    <View style={chipStyle} accessibilityLabel={accessibilityLabel}>
      {body}
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radius.full,
    borderWidth: 1,
  },
  chipMd: { paddingHorizontal: 12, paddingVertical: 6 },
  filter: { minHeight: 36, paddingHorizontal: 14 },
  pressed: { opacity: 0.85 },
  dot: { width: 6, height: 6, borderRadius: 3 },
  text: { fontSize: 11, fontFamily: FONT_SEMIBOLD, fontWeight: '600', letterSpacing: 0.1 },
  textMd: { fontSize: 13 },
});
