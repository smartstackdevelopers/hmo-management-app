import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';

import { IconName } from '@/constants/navigation';
import { theme } from '@/constants/theme';

interface TabIconProps {
  name: IconName;
  focusedName: IconName;
  focused: boolean;
  color: string;
  size?: number;
  /** Blue pill behind the active icon. */
  showPill?: boolean;
}

export function TabIcon({ name, focusedName, focused, color, size = 22, showPill = true }: TabIconProps) {
  const activePill = focused && showPill;

  return (
    <View style={styles.wrap}>
      <View style={[styles.hit, activePill && styles.pill]}>
        <Ionicons
          name={(focused ? focusedName : name) as keyof typeof Ionicons.glyphMap}
          size={activePill ? Math.min(size, 18) : size}
          color={activePill ? theme.colors.textInverse : color}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', justifyContent: 'center', minHeight: 32 },
  hit: {
    minWidth: 44,
    minHeight: 28,
    paddingHorizontal: 12,
    borderRadius: theme.radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pill: { backgroundColor: theme.colors.tabBarActive },
});
