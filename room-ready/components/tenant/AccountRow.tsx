import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { toneColors, type Tone } from '@/components/ui/Chip';
import { FONT_BOLD, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export function AccountRow({
  title,
  tone = 'blue',
  onPress,
  divider = false,
  danger = false,
}: {
  title: string;
  tone?: Tone;
  onPress: () => void;
  divider?: boolean;
  danger?: boolean;
}) {
  const colors = toneColors[tone];
  const letter = Array.from(title.trim())[0]?.toUpperCase() || '•';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={title}
      onPress={onPress}
      style={({ pressed }) => [styles.row, divider && styles.divider, pressed && styles.pressed]}
    >
      <View style={[styles.letter, { backgroundColor: colors.bg }]}>
        <Text style={[styles.letterText, { color: colors.text }]}>{letter}</Text>
      </View>
      <Text style={[styles.title, danger && styles.danger]} numberOfLines={1}>
        {title}
      </Text>
      <Ionicons name="chevron-forward" size={18} color={danger ? theme.colors.error : theme.colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 10,
  },
  divider: { borderBottomWidth: 1, borderBottomColor: theme.colors.borderLight },
  pressed: { backgroundColor: theme.colors.surfaceSecondary },
  letter: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  letterText: { fontFamily: FONT_BOLD, fontSize: 14 },
  title: { flex: 1, fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  danger: { color: theme.colors.error },
});
