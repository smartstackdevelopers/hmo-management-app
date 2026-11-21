import { StyleProp, Pressable, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface SectionProps {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export function Section({ title, subtitle, actionLabel, onAction, children, style }: SectionProps) {
  return (
    <View style={[styles.wrap, style]}>
      <View style={styles.head}>
        <View style={styles.copy}>
          <Text style={styles.title} accessibilityRole="header">{title}</Text>
          {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
        </View>
        {actionLabel && onAction && (
          <Pressable
            onPress={onAction}
            hitSlop={12}
            accessibilityRole="button"
            accessibilityLabel={`${actionLabel}: ${title}`}
            style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}
          >
            <Text style={styles.action}>{actionLabel}</Text>
          </Pressable>
        )}
      </View>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.lg },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
    gap: theme.spacing.sm,
  },
  copy: { flex: 1, minWidth: 0 },
  title: {
    fontSize: 17,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.2,
  },
  subtitle: { fontSize: 13, fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginTop: 2 },
  actionBtn: { minHeight: 32, justifyContent: 'center', paddingHorizontal: 4 },
  pressed: { opacity: 0.7 },
  action: { fontSize: 14, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.secondaryDark },
});
