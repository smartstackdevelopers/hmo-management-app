import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Chip, toneColors, type Tone } from '@/components/ui/Chip';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface AvatarProps {
  name: string;
  size?: number;
}

export function Avatar({ name, size = 48 }: AvatarProps) {
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <View
      style={[
        styles.avatar,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
        },
      ]}
    >
      <Text style={[styles.avatarText, { fontSize: size * 0.34 }]}>{initials}</Text>
    </View>
  );
}

interface ListRowProps {
  title: string;
  subtitle?: string;
  meta?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  iconColor?: string;
  iconBg?: string;
  /** Icon tile tone; `iconColor`/`iconBg` win when set. */
  tone?: Tone;
  onPress?: () => void;
  right?: React.ReactNode;
  /** Status chip shown on the right (ignored when `right` is set). */
  chipLabel?: string;
  chipTone?: Tone;
  chevron?: boolean;
  /** Bottom hairline, for rows stacked inside a Card. */
  divider?: boolean;
  accessibilityLabel?: string;
}

export function ListRow({
  title,
  subtitle,
  meta,
  icon,
  iconColor,
  iconBg,
  tone = 'blue',
  onPress,
  right,
  chipLabel,
  chipTone = 'gray',
  chevron = !!onPress,
  divider = false,
  accessibilityLabel,
}: ListRowProps) {
  const tileColors = toneColors[tone];
  const trailing = right ?? (chipLabel ? <Chip label={chipLabel} tone={chipTone} /> : null);

  const content = (
    <View style={styles.row}>
      {icon && (
        <View style={[styles.iconBox, { backgroundColor: iconBg ?? tileColors.bg }]}>
          <Ionicons name={icon} size={20} color={iconColor ?? tileColors.text} />
        </View>
      )}
      <View style={styles.copy}>
        <Text style={styles.title} numberOfLines={1}>{title}</Text>
        {subtitle && <Text style={styles.subtitle} numberOfLines={2}>{subtitle}</Text>}
        {meta && <Text style={styles.meta}>{meta}</Text>}
      </View>
      {trailing}
      {chevron && !right && (
        <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
      )}
    </View>
  );

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel ?? title}
        style={({ pressed }) => [styles.pressable, divider && styles.divider, pressed && styles.pressed]}
      >
        {content}
      </Pressable>
    );
  }

  return (
    <View style={[styles.pressable, divider && styles.divider]} accessibilityLabel={accessibilityLabel ?? title}>
      {content}
    </View>
  );
}

const styles = StyleSheet.create({
  avatar: {
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: theme.colors.accentSoft,
  },
  avatarText: {
    color: theme.colors.secondaryDark,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
  },
  pressable: {
    minHeight: 68,
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: theme.spacing.md,
  },
  divider: { borderBottomWidth: 1, borderBottomColor: theme.colors.borderLight },
  pressed: { backgroundColor: theme.colors.surfaceSecondary },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: { flex: 1, minWidth: 0 },
  title: {
    fontSize: 15,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    letterSpacing: -0.1,
  },
  subtitle: {
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  meta: {
    fontSize: 12,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textMuted,
    marginTop: 4,
  },
});
