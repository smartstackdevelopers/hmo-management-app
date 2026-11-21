import { StyleSheet, Text, View } from 'react-native';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface BrandHeaderProps {
  title?: string;
  subtitle?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  align?: 'center' | 'left';
  light?: boolean;
}

/** Centred HMore lockup used on auth and intro screens. */
export function BrandHeader({
  title,
  subtitle,
  size = 'md',
  align = 'center',
  light = false,
}: BrandHeaderProps) {
  const centered = align === 'center';

  return (
    <View style={[styles.wrap, centered ? styles.center : styles.left]}>
      <RoomReadyLogo size={size} centered={centered} layout="stack" light={light} shadow={false} />
      {title ? (
        <Text style={[styles.title, centered && styles.centerText, light && styles.titleLight]} accessibilityRole="header">
          {title}
        </Text>
      ) : null}
      {subtitle ? (
        <Text style={[styles.subtitle, centered && styles.centerText, light && styles.subtitleLight]}>{subtitle}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 4, marginBottom: theme.spacing.lg },
  center: { alignItems: 'center' },
  left: { alignItems: 'flex-start' },
  centerText: { textAlign: 'center' },
  title: {
    ...theme.typography.h2,
    fontFamily: FONT_BOLD,
    color: theme.colors.text,
    marginTop: theme.spacing.md,
  },
  titleLight: { color: theme.colors.textInverse },
  subtitle: {
    fontSize: 15,
    lineHeight: 22,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    maxWidth: 320,
    marginTop: 4,
  },
  subtitleLight: { color: 'rgba(255,255,255,0.82)' },
});
