import { Platform, StyleSheet, Text, View } from 'react-native';

import { LogoMark } from '@/components/LogoMark';
import { FONT_BOLD, FONT_SEMIBOLD, webShadow } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface RoomReadyLogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg';
  light?: boolean;
  centered?: boolean;
  markOnly?: boolean;
  shadow?: boolean;
}

const SIZES = {
  xs: { font: 14, icon: 28, gap: 8, radius: 8 },
  sm: { font: 18, icon: 34, gap: 10, radius: 10 },
  md: { font: 26, icon: 48, gap: 12, radius: 14 },
  lg: { font: 34, icon: 68, gap: 14, radius: 18 },
} as const;

export function RoomReadyLogo({
  size = 'md',
  light = false,
  centered,
  markOnly,
  shadow = true,
}: RoomReadyLogoProps) {
  const dims = SIZES[size];
  const shadowStyle = shadow ? (Platform.OS === 'web' ? webShadow('md') : theme.shadows.md) : undefined;

  const mark = (
    <View
      style={[
        styles.markWrap,
        {
          width: dims.icon,
          height: dims.icon,
          borderRadius: dims.radius,
        },
        shadowStyle,
      ]}
    >
      <LogoMark size={dims.icon} />
    </View>
  );

  if (markOnly) {
    return <View style={[styles.container, centered && styles.centered]}>{mark}</View>;
  }

  return (
    <View style={[styles.container, centered && styles.centered, { gap: dims.gap }]}>
      {mark}
      <View>
        <Text style={[styles.brand, { fontSize: dims.font }, light && styles.brandLight]}>
          Room <Text style={[styles.accent, light && styles.accentLight]}>Ready</Text>
        </Text>
        {size !== 'sm' && size !== 'xs' && (
          <Text style={[styles.tagline, light && styles.taglineLight]}>HMO property management</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  centered: { justifyContent: 'center' },
  markWrap: {
    overflow: 'hidden',
  },
  brand: {
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.primary,
    letterSpacing: -0.9,
  },
  brandLight: { color: theme.colors.textInverse },
  accent: { color: theme.colors.secondary },
  accentLight: { color: '#CCFBF1' },
  tagline: {
    fontSize: 11,
    fontFamily: FONT_SEMIBOLD,
    color: theme.colors.textSecondary,
    marginTop: 3,
    letterSpacing: 0.7,
    textTransform: 'uppercase',
    fontWeight: '600',
  },
  taglineLight: { color: 'rgba(255,255,255,0.72)' },
});
