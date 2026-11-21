import { Ionicons } from '@expo/vector-icons';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

import { toneColors, type Tone } from '@/components/ui/Chip';

interface IconTileProps {
  icon: keyof typeof Ionicons.glyphMap;
  tone?: Tone;
  size?: number;
  /** Overrides tone colours. */
  color?: string;
  bg?: string;
  round?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function IconTile({ icon, tone = 'blue', size = 40, color, bg, round = false, style }: IconTileProps) {
  const colors = toneColors[tone];
  return (
    <View
      style={[
        styles.tile,
        {
          width: size,
          height: size,
          borderRadius: round ? size / 2 : Math.round(size * 0.3),
          backgroundColor: bg ?? colors.bg,
        },
        style,
      ]}
    >
      <Ionicons name={icon} size={Math.round(size * 0.5)} color={color ?? colors.text} />
    </View>
  );
}

const styles = StyleSheet.create({
  tile: { alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
});
