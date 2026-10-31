import { ReactNode } from 'react';
import { ScrollView, ScrollViewProps, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

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
}

export function ScreenHeader({ title, subtitle, action, icon }: ScreenHeaderProps) {
  return (
    <View style={styles.header}>
      <View style={styles.headerText}>
        {icon && (
          <View style={styles.headerIcon}>
            <Ionicons name={icon} size={20} color={theme.colors.secondary} />
          </View>
        )}
        <View style={styles.headerCopy}>
          <Text style={styles.headerTitle} numberOfLines={1}>{title}</Text>
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
}

export function SectionHeader({ title, action }: SectionHeaderProps) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle} numberOfLines={1}>{title}</Text>
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
    width: 40,
    height: 40,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCopy: { flex: 1, minWidth: 0 },
  headerTitle: { ...theme.typography.h2, color: theme.colors.text },
  headerSubtitle: { fontSize: 14, color: theme.colors.textSecondary, marginTop: 2 },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
    marginTop: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  sectionTitle: { ...theme.typography.h3, color: theme.colors.text, flex: 1, minWidth: 0 },
});
