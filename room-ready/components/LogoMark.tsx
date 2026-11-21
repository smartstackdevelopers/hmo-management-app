import { StyleSheet, Text, View } from 'react-native';

import { FONT_BOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface LogoMarkProps {
  size?: number;
  /** Tile fill. Defaults to royal blue. */
  color?: string;
  /** Letter fill. Defaults to white. */
  letterColor?: string;
}

/** Blue rounded tile with a white H — the HMore app mark. */
export function LogoMark({ size = 44, color, letterColor }: LogoMarkProps) {
  const radius = Math.round(size * 0.28);
  const fontSize = Math.round(size * 0.48);

  return (
    <View
      accessibilityRole="image"
      accessibilityLabel="HMore"
      style={[
        styles.tile,
        {
          width: size,
          height: size,
          borderRadius: radius,
          backgroundColor: color ?? theme.colors.secondary,
        },
      ]}
    >
      <Text
        style={[
          styles.letter,
          {
            color: letterColor ?? theme.colors.textInverse,
            fontSize,
            lineHeight: Math.round(fontSize * 1.15),
          },
        ]}
      >
        H
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  tile: { alignItems: 'center', justifyContent: 'center' },
  letter: {
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    textAlign: 'center',
    includeFontPadding: false,
  },
});
