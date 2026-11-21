import { Ionicons } from '@expo/vector-icons';
import { ReactNode } from 'react';
import { Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface HeroCardProps {
  kicker?: string;
  value?: string;
  title?: string;
  subtitle?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  ctaLabel?: string;
  onCta?: () => void;
  ctaIcon?: keyof typeof Ionicons.glyphMap;
  /** `blue` = royal blue block, `navy` = brand navy block. */
  tone?: 'blue' | 'navy';
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function HeroCard({
  kicker,
  value,
  title,
  subtitle,
  icon,
  ctaLabel,
  onCta,
  ctaIcon = 'arrow-forward',
  tone = 'blue',
  children,
  style,
}: HeroCardProps) {
  return (
    <View style={[styles.card, tone === 'navy' && styles.navy, style]}>
      <View style={styles.glow} pointerEvents="none" />
      <View style={styles.top}>
        <View style={styles.copy}>
          {kicker ? <Text style={styles.kicker} numberOfLines={1}>{kicker}</Text> : null}
          {value ? (
            <Text style={styles.value} numberOfLines={1} adjustsFontSizeToFit>
              {value}
            </Text>
          ) : null}
          {title ? <Text style={styles.title} numberOfLines={2}>{title}</Text> : null}
          {subtitle ? <Text style={styles.subtitle} numberOfLines={3}>{subtitle}</Text> : null}
        </View>
        {icon ? (
          <View style={styles.iconWrap}>
            <Ionicons name={icon} size={22} color={theme.colors.textInverse} />
          </View>
        ) : null}
      </View>
      {children}
      {ctaLabel && onCta ? (
        <Pressable
          onPress={onCta}
          accessibilityRole="button"
          accessibilityLabel={ctaLabel}
          style={({ pressed }) => [styles.cta, pressed && styles.ctaPressed]}
        >
          <Text style={styles.ctaText}>{ctaLabel}</Text>
          <Ionicons name={ctaIcon} size={16} color={theme.colors.secondaryDark} />
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.secondaryDark,
    borderRadius: theme.radius.xl,
    padding: 20,
    overflow: 'hidden',
    marginBottom: theme.spacing.md,
  },
  navy: { backgroundColor: theme.colors.brand },
  glow: {
    position: 'absolute',
    width: 180,
    height: 180,
    borderRadius: 90,
    right: -60,
    top: -70,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  top: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  kicker: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.78)',
    letterSpacing: 0.4,
  },
  value: {
    fontSize: 30,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.textInverse,
    letterSpacing: -0.8,
    marginTop: 4,
  },
  title: {
    fontSize: 20,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.textInverse,
    letterSpacing: -0.3,
    marginTop: 4,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
    color: 'rgba(255,255,255,0.82)',
    marginTop: 4,
    lineHeight: 20,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.16)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cta: {
    marginTop: 16,
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    minHeight: 44,
    paddingHorizontal: 18,
    borderRadius: theme.radius.full,
    backgroundColor: theme.colors.surface,
  },
  ctaPressed: { opacity: 0.9 },
  ctaText: {
    fontSize: 14,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.secondaryDark,
  },
});
