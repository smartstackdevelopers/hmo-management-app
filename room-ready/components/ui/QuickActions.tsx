import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { toneColors, type Tone } from '@/components/ui/Chip';
import { FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export interface QuickAction {
  key: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  tone?: Tone;
  accessibilityLabel?: string;
}

interface QuickActionsProps {
  actions: QuickAction[];
  style?: StyleProp<ViewStyle>;
}

export function QuickActions({ actions, style }: QuickActionsProps) {
  return (
    <View style={[styles.row, style]}>
      {actions.map((action) => {
        const colors = toneColors[action.tone ?? 'blue'];
        return (
          <Pressable
            key={action.key}
            onPress={action.onPress}
            accessibilityRole="button"
            accessibilityLabel={action.accessibilityLabel ?? action.label}
            style={({ pressed }) => [styles.item, pressed && styles.pressed]}
          >
            <View style={[styles.circle, { backgroundColor: colors.bg }]}>
              <Ionicons name={action.icon} size={22} color={colors.text} />
            </View>
            <Text style={styles.label} numberOfLines={2}>
              {action.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.md,
  },
  item: { flex: 1, alignItems: 'center', minHeight: 44, paddingVertical: 4 },
  pressed: { opacity: 0.8 },
  circle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  label: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    textAlign: 'center',
  },
});
