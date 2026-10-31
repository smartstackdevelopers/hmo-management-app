import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

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
  onPress?: () => void;
  right?: React.ReactNode;
  chevron?: boolean;
}

export function ListRow({
  title,
  subtitle,
  meta,
  icon,
  iconColor = theme.colors.secondary,
  iconBg = theme.colors.accentLight,
  onPress,
  right,
  chevron = !!onPress,
}: ListRowProps) {
  const content = (
    <View style={styles.row}>
      {icon && (
        <View style={[styles.iconBox, { backgroundColor: iconBg }]}>
          <Ionicons name={icon} size={20} color={iconColor} />
        </View>
      )}
      <View style={styles.copy}>
        <Text style={styles.title} numberOfLines={1}>{title}</Text>
        {subtitle && <Text style={styles.subtitle} numberOfLines={2}>{subtitle}</Text>}
        {meta && <Text style={styles.meta}>{meta}</Text>}
      </View>
      {right}
      {chevron && !right && (
        <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
      )}
    </View>
  );

  if (onPress) {
    return (
      <Pressable onPress={onPress} style={({ pressed }) => [styles.pressable, pressed && styles.pressed]}>
        {content}
      </Pressable>
    );
  }

  return <View style={styles.pressable}>{content}</View>;
}

const styles = StyleSheet.create({
  avatar: {
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: '#99F6E4',
  },
  avatarText: {
    color: theme.colors.secondaryDark,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
  },
  pressable: {
    paddingVertical: 14,
    paddingHorizontal: theme.spacing.md,
  },
  pressed: { backgroundColor: theme.colors.surfaceMuted },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.md,
  },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: theme.radius.md,
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
    color: theme.colors.textMuted,
    marginTop: 4,
  },
});
