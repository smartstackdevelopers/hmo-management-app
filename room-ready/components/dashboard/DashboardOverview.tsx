import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Chip } from '@/components/ui/Chip';
import { Avatar } from '@/components/ui/ListRow';
import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { UserRole } from '@/types';

type StatusTone = 'success' | 'warning' | 'error' | 'neutral';

interface DashboardOverviewProps {
  firstName: string;
  lastName?: string;
  role: UserRole;
  subtitle: string;
  status: { label: string; tone: StatusTone };
  unreadCount?: number;
}

const STATUS_TONE: Record<StatusTone, 'green' | 'amber' | 'red' | 'gray'> = {
  success: 'green',
  warning: 'amber',
  error: 'red',
  neutral: 'gray',
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
  const portfolio = role === 'landlord' || role === 'property_manager';
  const displayName = `${firstName}${lastName ? ` ${lastName}` : ''}`;

  return (
    <View style={[styles.shell, { paddingTop: insets.top + 8 }]}>
      <FocusStatusBar style="dark" />
      <View style={styles.topBar}>
        <View style={styles.topCopy}>
          <Text style={styles.kicker} numberOfLines={1}>
            {portfolio ? 'Portfolio overview' : getGreeting()}
          </Text>
          <Text style={styles.name} numberOfLines={1}>
            {firstName}
          </Text>
          {!portfolio && subtitle ? (
            <Text style={styles.subtitle} numberOfLines={2}>
              {subtitle}
            </Text>
          ) : null}
        </View>
        <Pressable
          onPress={() => router.push(unreadCount > 0 ? '/(app)/notifications' : '/(app)/(tabs)/more')}
          accessibilityRole="button"
          accessibilityLabel={unreadCount > 0 ? `${unreadCount} alerts` : 'Account'}
        >
          <Avatar name={displayName} size={48} />
          {unreadCount > 0 ? (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{unreadCount > 9 ? '9+' : unreadCount}</Text>
            </View>
          ) : null}
        </Pressable>
      </View>
      {!portfolio ? <Chip label={status.label} tone={STATUS_TONE[status.tone]} style={styles.status} /> : null}
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
    paddingBottom: theme.spacing.sm,
    backgroundColor: theme.colors.background,
    width: '100%',
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: theme.spacing.sm,
  },
  topCopy: { flex: 1, minWidth: 0 },
  kicker: {
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
  },
  name: {
    fontSize: 32,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.8,
    marginTop: 2,
  },
  subtitle: {
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 4,
    lineHeight: 20,
  },
  badge: {
    position: 'absolute',
    top: -2,
    right: -2,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: theme.colors.secondaryDark,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
    borderWidth: 2,
    borderColor: theme.colors.background,
  },
  badgeText: { color: theme.colors.textInverse, fontSize: 10, fontFamily: FONT_BOLD, fontWeight: '700' },
  status: { marginTop: theme.spacing.sm },
});
