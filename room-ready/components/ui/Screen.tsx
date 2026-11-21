import { ReactNode } from 'react';
import { ScrollView, ScrollViewProps, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { useTabClearance } from '@/hooks/useLayout';
import { theme } from '@/constants/theme';

interface ScreenProps extends ScrollViewProps {
  children: ReactNode;
  scroll?: boolean;
  padded?: boolean;
  fullBleedHeader?: boolean;
  style?: ViewStyle;
  header?: ReactNode;
}

export function Screen({
  children,
  scroll = true,
  padded = true,
  fullBleedHeader = false,
  style,
  header,
  contentContainerStyle,
  ...props
}: ScreenProps) {
  const bottomPad = useTabClearance();
  const padding = padded ? theme.spacing.md : 0;

  const body = fullBleedHeader ? (
    <>
      {header}
      <View style={{ paddingHorizontal: padding }}>{children}</View>
    </>
  ) : (
    <>
      {header}
      {children}
    </>
  );

  if (!scroll) {
    return (
      <View style={[styles.screen, { paddingBottom: bottomPad }, style]}>
        {body}
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.screen, style]}
      contentContainerStyle={[
        fullBleedHeader ? undefined : { padding },
        contentContainerStyle,
        { paddingBottom: bottomPad },
      ]}
      showsVerticalScrollIndicator={false}
      {...props}
    >
      {body}
    </ScrollView>
  );
}

interface ScreenHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  icon?: keyof typeof Ionicons.glyphMap;
  /** Small label above the title. */
  eyebrow?: string;
}

export function ScreenHeader({ title, subtitle, action, icon, eyebrow }: ScreenHeaderProps) {
  return (
    <View style={styles.header}>
      <View style={styles.headerText}>
        {icon && (
          <View style={styles.headerIcon}>
            <Ionicons name={icon} size={20} color={theme.colors.secondaryDark} />
          </View>
        )}
        <View style={styles.headerCopy}>
          {eyebrow ? <Text style={styles.eyebrow} numberOfLines={1}>{eyebrow}</Text> : null}
          <Text style={styles.headerTitle} numberOfLines={1} accessibilityRole="header">{title}</Text>
          {subtitle ? <Text style={styles.headerSubtitle} numberOfLines={2}>{subtitle}</Text> : null}
        </View>
      </View>
      {action}
    </View>
  );
}

interface SectionHeaderProps {
  title: string;
  action?: ReactNode;
  subtitle?: string;
}

export function SectionHeader({ title, action, subtitle }: SectionHeaderProps) {
  return (
    <View style={styles.sectionHeader}>
      <View style={styles.headerCopy}>
        <Text style={styles.sectionTitle} numberOfLines={1} accessibilityRole="header">{title}</Text>
        {subtitle ? <Text style={styles.sectionSubtitle} numberOfLines={2}>{subtitle}</Text> : null}
      </View>
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  headerText: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 },
  headerIcon: {
    width: 44,
    height: 44,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCopy: { flex: 1, minWidth: 0 },
  eyebrow: {
    ...theme.typography.overline,
    fontFamily: FONT_SEMIBOLD,
    color: theme.colors.secondaryDark,
    marginBottom: 2,
    textTransform: 'uppercase',
  },
  headerTitle: { ...theme.typography.h2, fontFamily: FONT_BOLD, color: theme.colors.text },
  headerSubtitle: { fontSize: 14, lineHeight: 20, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
    marginTop: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  sectionTitle: { ...theme.typography.h3, fontFamily: FONT_BOLD, color: theme.colors.text },
  sectionSubtitle: { fontSize: 13, lineHeight: 18, fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginTop: 2 },
});
