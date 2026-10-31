import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { theme } from '@/constants/theme';
import { UserRole } from '@/types';

interface DashboardHeroProps {
  firstName: string;
  lastName?: string;
  role: UserRole;
  unreadCount?: number;
  subtitle?: string;
}

export function DashboardHero({ firstName, unreadCount = 0, subtitle }: DashboardHeroProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.shell, { paddingTop: insets.top + 12 }]}>
      <FocusStatusBar style="dark" />
      <View style={styles.row}>
        <View style={styles.copy}>
          <Text style={styles.greeting}>{getGreeting()}, {firstName}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <View style={styles.actions}>
          <Pressable style={styles.btn} onPress={() => router.push('/(app)/notifications')}>
            <Ionicons name="notifications-outline" size={22} color={theme.colors.text} />
            {unreadCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{unreadCount > 9 ? '9+' : unreadCount}</Text>
              </View>
            )}
          </Pressable>
          <Pressable style={styles.btn} onPress={() => router.push('/(app)/(tabs)/more')}>
            <Ionicons name="person-outline" size={22} color={theme.colors.text} />
          </Pressable>
        </View>
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
    paddingBottom: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderLight,
    backgroundColor: theme.colors.background,
  },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  copy: { flex: 1 },
  greeting: {
    fontSize: 24,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.5,
    lineHeight: 30,
  },
  subtitle: { fontSize: 14, color: theme.colors.textSecondary, marginTop: 4, lineHeight: 20 },
  actions: { flexDirection: 'row', gap: 4 },
  btn: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: theme.radius.md,
  },
  badge: {
    position: 'absolute',
    top: 4,
    right: 4,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: theme.colors.error,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 3,
  },
  badgeText: { color: '#fff', fontSize: 9, fontWeight: '700' },
});
