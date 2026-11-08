import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Avatar, ListRow } from '@/components/ui/ListRow';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useTabClearance } from '@/hooks/useLayout';
import { useAuth } from '@/contexts/AuthContext';
import { getOwnTenant } from '@/lib/hmore/services/tenants';
import { ROLE_LABELS } from '@/types';

export function HmoreAccount() {
  const { user, hmore, signOut } = useAuth();
  const bottomPad = useTabClearance();
  const isTenant = hmore?.rbac.active_role === 'tenant';
  const userId = hmore?.auth.id ?? '';
  const tenantQuery = useQuery({
    queryKey: ['hmore', 'tenant', userId],
    queryFn: () => getOwnTenant(userId),
    enabled: isTenant && !!userId,
  });
  const tenant = tenantQuery.data;

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/welcome');
  }

  const displayName = tenant?.preferred_name || `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim();

  return (
    <ScrollView style={styles.container} contentContainerStyle={[styles.content, { paddingBottom: bottomPad }]}>
      <Text style={styles.pageTitle}>Account</Text>
      <Card style={styles.profile}>
        <View style={styles.profileRow}>
          <Avatar name={displayName || 'Account'} />
          <View style={styles.profileCopy}>
            <Text style={styles.name} numberOfLines={1}>{displayName || 'Account'}</Text>
            <Text style={styles.email} numberOfLines={1}>{tenant?.email || user?.email}</Text>
            {user?.role ? <Text style={styles.role}>{ROLE_LABELS[user.role]}</Text> : null}
          </View>
        </View>
        {isTenant ? (
          <Text style={styles.note}>
            Profile details come from your housing record and cannot be edited here.
            {tenant?.phone ? ` Phone on record: ${tenant.phone}.` : ''}
            {tenant?.tenancy_reference ? ` Reference ${tenant.tenancy_reference}.` : ''}
          </Text>
        ) : (
          <Text style={styles.note}>Signed in with your organisation account.</Text>
        )}
      </Card>

      <Card padded={false}>
        <ListRow title="Alerts" icon="notifications-outline" onPress={() => router.push('/(app)/notifications')} />
        <View style={styles.divider} />
        <ListRow title="My files" icon="folder-outline" onPress={() => router.push('/(app)/documents')} />
        {isTenant ? (
          <>
            <View style={styles.divider} />
            <ListRow title="My home" icon="business-outline" onPress={() => router.push('/(app)/(tabs)/tenancy')} />
            <View style={styles.divider} />
            <ListRow title="Support" icon="people-outline" onPress={() => router.push('/(app)/(tabs)/support')} />
            <View style={styles.divider} />
            <ListRow title="Assistant" icon="chatbubble-ellipses-outline" onPress={() => router.push('/(app)/assistant')} />
            <View style={styles.divider} />
            <ListRow title="Local services" icon="location-outline" onPress={() => router.push('/(app)/community')} />
            <View style={styles.divider} />
            <ListRow title="Jobs and training" icon="briefcase-outline" onPress={() => router.push('/(app)/jobs')} />
          </>
        ) : null}
        <View style={styles.divider} />
        <ListRow title="Language and accessibility" icon="accessibility-outline" onPress={() => router.push('/(app)/accessibility')} />
      </Card>

      <Text style={styles.version}>HMore tenant app</Text>
      <Button title="Sign out" variant="outline" onPress={handleSignOut} fullWidth />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md },
  pageTitle: { fontSize: 28, fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.md, letterSpacing: -0.5 },
  profile: { marginBottom: theme.spacing.md },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  profileCopy: { flex: 1, minWidth: 0 },
  name: { fontSize: 18, fontFamily: FONT_SEMIBOLD, color: theme.colors.text },
  email: { fontSize: 14, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 },
  role: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    color: theme.colors.secondaryDark,
    marginTop: 6,
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.accentLight,
    overflow: 'hidden',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radius.full,
  },
  note: { fontFamily: FONT_MEDIUM, fontSize: 13, lineHeight: 18, color: theme.colors.textSecondary, marginTop: theme.spacing.md },
  divider: { height: 1, backgroundColor: theme.colors.borderLight, marginLeft: 60 },
  version: { textAlign: 'center', color: theme.colors.textMuted, fontSize: 12, fontFamily: FONT_MEDIUM, marginVertical: theme.spacing.lg },
});
