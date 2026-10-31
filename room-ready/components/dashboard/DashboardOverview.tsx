import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Avatar } from '@/components/ui/ListRow';
import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { UserRole } from '@/types';

import { DASHBOARD_ACTIONS } from './dashboardActions';

type StatusTone = 'success' | 'warning' | 'error' | 'neutral';

interface DashboardOverviewProps {
  firstName: string;
  lastName?: string;
  role: UserRole;
  subtitle: string;
  status: { label: string; tone: StatusTone };
  unreadCount?: number;
}

const TONE_STYLES: Record<StatusTone, { bg: string; text: string; dot: string }> = {
  success: { bg: theme.colors.successLight, text: theme.colors.success, dot: theme.colors.success },
  warning: { bg: theme.colors.warningLight, text: theme.colors.warning, dot: theme.colors.warning },
  error: { bg: theme.colors.errorLight, text: theme.colors.error, dot: theme.colors.error },
  neutral: { bg: theme.colors.surfaceMuted, text: theme.colors.textSecondary, dot: theme.colors.textMuted },
};

export function DashboardOverview({
  firstName,
  lastName,
  role,
  subtitle,
  status,
  unreadCount = 0,
}: DashboardOverviewProps) {
  const insets = useSafeAreaInsets();
  const actions = DASHBOARD_ACTIONS[role].slice(0, 3);
  const tone = TONE_STYLES[status.tone];
  const displayName = `${firstName}${lastName ? ` ${lastName.charAt(0)}.` : ''}`;

  return (
    <View style={[styles.shell, { paddingTop: insets.top + 10 }]}>
      <FocusStatusBar style="dark" />

      <View style={styles.topBar}>
        <View style={styles.topCopy}>
          <Text style={styles.greeting} numberOfLines={1}>
            {getGreeting()}, {firstName}
          </Text>
          <Text style={styles.subtitle} numberOfLines={2}>{subtitle}</Text>
        </View>
        <View style={styles.topActions}>
          <Pressable
            style={styles.iconBtn}
            onPress={() => router.push('/(app)/notifications')}
            accessibilityLabel="Alerts"
          >
            <Ionicons name="notifications-outline" size={20} color={theme.colors.text} />
            {unreadCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{unreadCount > 9 ? '9+' : unreadCount}</Text>
              </View>
            )}
          </Pressable>
          <Pressable
            style={styles.iconBtn}
            onPress={() => router.push('/(app)/(tabs)/more')}
            accessibilityLabel="Account"
          >
            <Avatar name={displayName} size={34} />
          </Pressable>
        </View>
      </View>

      <View style={[styles.statusPill, { backgroundColor: tone.bg }]}>
        <View style={[styles.statusDot, { backgroundColor: tone.dot }]} />
        <Text style={[styles.statusText, { color: tone.text }]} numberOfLines={1}>{status.label}</Text>
      </View>

      <View style={styles.actions}>
        {actions.map((action) => (
          <Pressable
            key={action.label}
            style={({ pressed }) => [
              styles.action,
              action.primary ? styles.actionPrimary : styles.actionSecondary,
              pressed && styles.actionPressed,
            ]}
            onPress={() => router.push(action.route as never)}
          >
            <View style={[styles.actionIcon, action.primary && styles.actionIconPrimary]}>
              <Ionicons
                name={action.icon}
                size={18}
                color={action.primary ? theme.colors.textInverse : theme.colors.secondary}
              />
            </View>
            <Text
              style={[styles.actionLabel, action.primary && styles.actionLabelPrimary]}
              numberOfLines={1}
            >
              {action.label}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

const styles = StyleSheet.create({
  shell: {
    paddingHorizontal: theme.spacing.md,
    paddingBottom: theme.spacing.md,
    backgroundColor: theme.colors.backgroundAlt,
    gap: theme.spacing.md,
    width: '100%',
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: theme.spacing.sm,
  },
  topCopy: { flex: 1, minWidth: 0 },
  greeting: {
    fontSize: 26,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.6,
    lineHeight: 32,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 4,
    lineHeight: 20,
  },
  topActions: { flexDirection: 'row', alignItems: 'center', gap: 8, flexShrink: 0 },
  iconBtn: {
    width: 42,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: theme.radius.full,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  badge: {
    position: 'absolute',
    top: 2,
    right: 2,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: theme.colors.error,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 3,
    borderWidth: 2,
    borderColor: theme.colors.surface,
  },
  badgeText: { color: '#fff', fontSize: 9, fontFamily: FONT_BOLD, fontWeight: '700' },
  statusPill: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: theme.radius.full,
    maxWidth: '100%',
  },
  statusDot: { width: 7, height: 7, borderRadius: 4 },
  statusText: { fontSize: 13, fontFamily: FONT_SEMIBOLD, fontWeight: '600', flexShrink: 1 },
  actions: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    width: '100%',
  },
  action: {
    flex: 1,
    minWidth: 0,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    paddingHorizontal: 6,
    borderRadius: theme.radius.lg,
  },
  actionPrimary: {
    backgroundColor: theme.colors.secondary,
  },
  actionSecondary: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  actionPressed: { opacity: 0.9, transform: [{ scale: 0.98 }] },
  actionIcon: {
    width: 36,
    height: 36,
    borderRadius: theme.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.accentLight,
  },
  actionIconPrimary: {
    backgroundColor: 'rgba(255,255,255,0.18)',
  },
  actionLabel: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    textAlign: 'center',
  },
  actionLabelPrimary: {
    color: theme.colors.textInverse,
  },
});
