import { Ionicons } from '@expo/vector-icons';
import { ActivityIndicator, Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { Button } from '@/components/ui/Button';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

type StateTone = 'info' | 'neutral' | 'offline';

const toneStyle: Record<StateTone, { bg: string; fg: string }> = {
  info: { bg: theme.colors.accentLight, fg: theme.colors.secondaryDark },
  neutral: { bg: theme.colors.surfaceMuted, fg: theme.colors.textSecondary },
  offline: { bg: theme.colors.surfaceMuted, fg: '#475569' },
};

interface StateActions {
  actionLabel?: string;
  onAction?: () => void;
  secondaryLabel?: string;
  onSecondary?: () => void;
  compact?: boolean;
  style?: StyleProp<ViewStyle>;
}

function StateShell({
  icon,
  iconColor,
  iconBg,
  title,
  message,
  actionLabel,
  onAction,
  secondaryLabel,
  onSecondary,
  compact = false,
  style,
  live,
}: StateActions & {
  icon: keyof typeof Ionicons.glyphMap;
  iconColor: string;
  iconBg: string;
  title: string;
  message?: string;
  live?: boolean;
}) {
  const hasAction = Boolean(actionLabel && onAction);
  const hasSecondary = Boolean(secondaryLabel && onSecondary);
  const hasActions = hasAction || hasSecondary;

  return (
    <View style={[styles.center, !hasActions && styles.centered, compact && styles.compact, style]}>
      <View style={styles.copy}>
        <View style={[styles.iconCircle, { backgroundColor: iconBg }]}>
          <Ionicons name={icon} size={32} color={iconColor} />
        </View>
        <Text style={styles.title} accessibilityRole="header">
          {title}
        </Text>
        {message ? (
          <Text style={styles.message} accessibilityLiveRegion={live ? 'polite' : undefined}>
            {message}
          </Text>
        ) : null}
      </View>
      {hasActions ? (
        <View style={[styles.actions, compact && styles.actionsInline]}>
          {hasAction ? (
            <Button title={actionLabel!} onPress={onAction} size={compact ? 'md' : 'lg'} fullWidth />
          ) : null}
          {hasSecondary ? (
            <Pressable
              onPress={onSecondary}
              accessibilityRole="button"
              accessibilityLabel={secondaryLabel}
              style={styles.linkBtn}
            >
              <Text style={styles.link}>{secondaryLabel}</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

export function LoadingScreen({ message = 'Loading...', style }: { message?: string; style?: StyleProp<ViewStyle> }) {
  return (
    <View style={[styles.center, style]}>
      <RoomReadyLogo size="sm" centered markOnly shadow={false} />
      <ActivityIndicator size="large" color={theme.colors.secondary} style={styles.spinner} accessibilityLabel={message} />
      <Text style={styles.muted}>{message}</Text>
    </View>
  );
}

export function EmptyState({
  title,
  message,
  icon = 'folder-open-outline',
  actionLabel,
  onAction,
  secondaryLabel,
  onSecondary,
  tone = 'info',
  compact = false,
  style,
}: {
  title: string;
  message?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  actionLabel?: string;
  onAction?: () => void;
  secondaryLabel?: string;
  onSecondary?: () => void;
  tone?: StateTone;
  compact?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const colors = toneStyle[tone];
  return (
    <StateShell
      icon={icon}
      iconColor={colors.fg}
      iconBg={colors.bg}
      title={title}
      message={message}
      actionLabel={actionLabel}
      onAction={onAction}
      secondaryLabel={secondaryLabel}
      onSecondary={onSecondary}
      compact={compact}
      style={style}
    />
  );
}

export function ErrorState({
  message,
  onRetry,
  title = 'Something went wrong',
  icon = 'warning',
  actionLabel = 'Try again',
  secondaryLabel,
  onSecondary,
  compact = false,
  style,
}: {
  message: string;
  onRetry?: () => void;
  title?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  actionLabel?: string;
  secondaryLabel?: string;
  onSecondary?: () => void;
  compact?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <StateShell
      icon={icon}
      iconColor={theme.colors.error}
      iconBg={theme.colors.errorLight}
      title={title}
      message={message}
      actionLabel={onRetry ? actionLabel : undefined}
      onAction={onRetry}
      secondaryLabel={secondaryLabel}
      onSecondary={onSecondary}
      compact={compact}
      style={style}
      live
    />
  );
}

export function OfflineState({
  title = "You're offline",
  message = 'You can keep working. Logs and repairs will send automatically when you reconnect.',
  actionLabel,
  onAction,
  secondaryLabel,
  onSecondary,
  compact = false,
  style,
}: {
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryLabel?: string;
  onSecondary?: () => void;
  compact?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <EmptyState
      title={title}
      message={message}
      icon="cloud-offline-outline"
      tone="offline"
      actionLabel={actionLabel}
      onAction={onAction}
      secondaryLabel={secondaryLabel}
      onSecondary={onSecondary}
      compact={compact}
      style={style}
    />
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.xxl,
    paddingBottom: theme.spacing.md,
    backgroundColor: theme.colors.background,
    width: '100%',
  },
  centered: { justifyContent: 'center', paddingTop: theme.spacing.xl },
  compact: {
    flex: 0,
    backgroundColor: 'transparent',
    paddingVertical: theme.spacing.lg,
    justifyContent: 'flex-start',
  },
  copy: { alignItems: 'center', maxWidth: 320 },
  spinner: { marginTop: theme.spacing.lg },
  muted: {
    color: theme.colors.textSecondary,
    marginTop: 12,
    fontSize: 14,
    lineHeight: 20,
    fontFamily: FONT_MEDIUM,
    textAlign: 'center',
  },
  iconCircle: {
    width: 88,
    height: 88,
    borderRadius: 44,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.lg,
  },
  title: {
    fontSize: 20,
    lineHeight: 26,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    textAlign: 'center',
    letterSpacing: -0.3,
  },
  message: {
    color: theme.colors.textSecondary,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 22,
    fontSize: 15,
    fontFamily: FONT_MEDIUM,
  },
  actions: {
    width: '100%',
    maxWidth: 360,
    marginTop: 'auto',
    paddingTop: theme.spacing.lg,
  },
  actionsInline: { marginTop: theme.spacing.lg },
  linkBtn: {
    minHeight: 44,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
  link: {
    color: theme.colors.secondaryDark,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    fontSize: 15,
  },
});
