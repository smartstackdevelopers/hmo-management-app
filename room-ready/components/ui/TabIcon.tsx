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
}

export function TabIcon({ name, focusedName, focused, color, size = 24 }: TabIconProps) {
  return (
    <View style={styles.wrap}>
      <Ionicons name={(focused ? focusedName : name) as keyof typeof Ionicons.glyphMap} size={size} color={color} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', justifyContent: 'center', height: 28 },
});
