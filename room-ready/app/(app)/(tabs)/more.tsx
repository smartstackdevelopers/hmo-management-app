import { router } from 'expo-router';
import { Linking, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Avatar, ListRow } from '@/components/ui/ListRow';
import { SIMPLE } from '@/constants/simpleCopy';
import { BIRMINGHAM_COUNCIL } from '@/constants/birmingham';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { roleHasAccess, ROUTE_ROLES } from '@/constants/permissions';
import { UK_CONFIG } from '@/constants/uk';
import { useAuth } from '@/contexts/AuthContext';
import { useTabClearance } from '@/hooks/useLayout';
import { useNotifications } from '@/hooks/useApi';
import { ROLE_LABELS } from '@/types';

export default function MoreScreen() {
  const { user, signOut } = useAuth();
  const bottomPad = useTabClearance();
  const { data: notifData, refetch: refetchNotifs, isRefetching } = useNotifications();
  const unreadCount = notifData?.unreadCount ?? 0;
  const showCompliance = roleHasAccess(user?.role, ROUTE_ROLES.complianceMenu);
  const role = user?.role;

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/welcome');
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, { paddingBottom: bottomPad }]}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={refetchNotifs}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Text style={styles.pageTitle}>Account</Text>
      <Card style={styles.profile}>
        <View style={styles.profileRow}>
          <Avatar name={`${user?.firstName ?? ''} ${user?.lastName ?? ''}`} />
          <View style={styles.profileCopy}>
            <Text style={styles.name} numberOfLines={1}>{user?.firstName} {user?.lastName}</Text>
            <Text style={styles.email} numberOfLines={1}>{user?.email}</Text>
            {role && <Text style={styles.role}>{ROLE_LABELS[role]}</Text>}
          </View>
        </View>
      </Card>

      <Card padded={false}>
        <ListRow
          title={SIMPLE.account.notifications}
          subtitle={unreadCount > 0 ? `${unreadCount} new` : undefined}
          icon="notifications-outline"
          onPress={() => router.push('/(app)/notifications')}
          right={unreadCount > 0 ? <Badge label={String(unreadCount)} variant="error" format={false} /> : undefined}
          chevron={unreadCount === 0}
        />
        <View style={styles.divider} />
        <ListRow title={SIMPLE.account.files} icon="folder-outline" onPress={() => router.push('/(app)/documents')} />
        {(role === 'landlord' || role === 'property_manager') && (
          <>
            <View style={styles.divider} />
            <ListRow title="Room listings" icon="list-outline" onPress={() => router.push('/(app)/(tabs)/listings')} />
            <View style={styles.divider} />
            <ListRow title="Property checks" icon="shield-checkmark-outline" onPress={() => router.push('/(app)/(tabs)/compliance')} />
          </>
        )}
        {role === 'tenant' && (
          <>
            <View style={styles.divider} />
            <ListRow title="My home" icon="business-outline" onPress={() => router.push('/(app)/(tabs)/tenancy')} />
            <View style={styles.divider} />
            <ListRow title="Find a room" icon="search-outline" onPress={() => router.push('/(app)/(tabs)/find')} />
            <View style={styles.divider} />
            <ListRow title="Saved rooms" icon="heart-outline" onPress={() => router.push('/(app)/wishlist')} />
          </>
        )}
        {showCompliance && role !== 'landlord' && role !== 'property_manager' && (
          <>
            <View style={styles.divider} />
            <ListRow title="Property checks" icon="shield-checkmark-outline" onPress={() => router.push('/(app)/(tabs)/compliance')} />
          </>
        )}
        {role === 'property_manager' && (
          <>
            <View style={styles.divider} />
            <ListRow title="Inspections" icon="clipboard-outline" onPress={() => router.push('/(app)/(tabs)/inspections')} />
          </>
        )}
        <View style={styles.divider} />
        <ListRow title={SIMPLE.account.password} icon="lock-closed-outline" onPress={() => router.push('/(app)/security')} />
        <View style={styles.divider} />
        <ListRow title={SIMPLE.account.help} icon="help-circle-outline" onPress={() => Linking.openURL(BIRMINGHAM_COUNCIL.housingStandardsUrl)} />
      </Card>

      <Text style={styles.version}>Room Ready · {UK_CONFIG.country}</Text>
      <Button title={SIMPLE.account.signOut} variant="outline" onPress={handleSignOut} fullWidth />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md },
  pageTitle: {
    fontSize: 28,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
    letterSpacing: -0.5,
  },
  profile: { marginBottom: theme.spacing.md },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  profileCopy: { flex: 1, minWidth: 0 },
  name: { fontSize: 18, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  email: { fontSize: 14, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 },
  role: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    color: theme.colors.secondaryDark,
    fontWeight: '600',
    marginTop: 6,
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.accentLight,
    overflow: 'hidden',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radius.full,
  },
  divider: { height: 1, backgroundColor: theme.colors.borderLight, marginLeft: 60 },
  version: {
    textAlign: 'center',
    color: theme.colors.textMuted,
    fontSize: 12,
    fontFamily: FONT_MEDIUM,
    marginVertical: theme.spacing.lg,
  },
});
