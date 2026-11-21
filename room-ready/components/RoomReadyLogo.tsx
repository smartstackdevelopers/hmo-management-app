import { Platform, StyleSheet, Text, View } from 'react-native';

import { LogoMark } from '@/components/LogoMark';
import { FONT_BOLD, FONT_MEDIUM, webShadow } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface RoomReadyLogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg';
  light?: boolean;
  centered?: boolean;
  markOnly?: boolean;
  shadow?: boolean;
  /** `stack` places the wordmark under the mark. `row` keeps them side by side. */
  layout?: 'row' | 'stack';
  /** Defaults to HMore. */
  wordmark?: string;
  showTagline?: boolean;
}

const SIZES = {
  xs: { font: 15, icon: 32, gap: 8 },
  sm: { font: 18, icon: 52, gap: 10 },
  md: { font: 22, icon: 64, gap: 12 },
  lg: { font: 26, icon: 72, gap: 14 },
} as const;

export function RoomReadyLogo({
  size = 'md',
  light = false,
  centered,
  markOnly,
  shadow = true,
  layout = 'stack',
  wordmark = 'HMore',
  showTagline = false,
}: RoomReadyLogoProps) {
  const dims = SIZES[size];
  const shadowStyle = shadow ? (Platform.OS === 'web' ? webShadow('sm') : theme.shadows.sm) : undefined;
  const alignCenter = centered || layout === 'stack';

  const mark = (
    <View style={[{ width: dims.icon, height: dims.icon }, shadowStyle]}>
      <LogoMark size={dims.icon} />
    </View>
  );

  if (markOnly) {
    return <View style={[styles.container, centered && styles.centered]}>{mark}</View>;
  }

  return (
    <View
      style={[
        styles.container,
        layout === 'stack' && styles.stack,
        alignCenter && styles.centered,
        { gap: layout === 'stack' ? Math.max(8, dims.gap - 2) : dims.gap },
      ]}
    >
      {mark}
      <View style={alignCenter && styles.copyCenter}>
        <Text
          style={[
            styles.brand,
            { fontSize: dims.font },
            alignCenter && styles.textCenter,
            light && styles.brandLight,
          ]}
        >
          {wordmark}
        </Text>
        {showTagline ? (
          <Text style={[styles.tagline, alignCenter && styles.textCenter, light && styles.taglineLight]}>
            Housing and support
          </Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stack: { flexDirection: 'column' },
  centered: { justifyContent: 'center', alignItems: 'center' },
  copyCenter: { alignItems: 'center' },
  textCenter: { textAlign: 'center' },
  brand: {
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.6,
  },
  brandLight: { color: theme.colors.textInverse },
  tagline: {
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  taglineLight: { color: 'rgba(255,255,255,0.78)' },
});
