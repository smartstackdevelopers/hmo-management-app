import { router } from 'expo-router';
import { Linking, StyleSheet, Text, View } from 'react-native';

import { StaffMore } from '@/components/staff/StaffMore';
import { AccountRow } from '@/components/tenant/AccountRow';
import { HmoreAccount } from '@/components/tenant/HmoreAccount';
import { staffShellActive } from '@/constants/navigation';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Avatar } from '@/components/ui/ListRow';
import { Screen } from '@/components/ui/Screen';
import { Section } from '@/components/ui/Section';
import { SIMPLE } from '@/constants/simpleCopy';
import { BIRMINGHAM_COUNCIL } from '@/constants/birmingham';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { roleHasAccess, ROUTE_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { ROLE_LABELS } from '@/types';

function LegacyMoreScreen() {
  const { user, signOut } = useAuth();
  const showCompliance = roleHasAccess(user?.role, ROUTE_ROLES.complianceMenu);
  const role = user?.role;
  const name = `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim();
  const email = user?.email?.trim() ?? '';

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/welcome');
  }

  return (
    <Screen>
      <Text style={styles.pageTitle}>Account</Text>
      <Card style={styles.profile}>
        <View style={styles.profileRow}>
          <Avatar name={name || email || 'Account'} />
          <View style={styles.profileCopy}>
            {name ? (
              <Text style={styles.name} numberOfLines={1}>
                {name}
              </Text>
            ) : null}
            {email ? (
              <Text style={styles.email} numberOfLines={1}>
                {email}
              </Text>
            ) : null}
            {role ? <Chip label={ROLE_LABELS[role]} tone="blue" size="md" /> : null}
          </View>
        </View>
      </Card>

      <Section title="My account">
        <Card padded={false}>
          <AccountRow title={SIMPLE.account.notifications} tone="blue" onPress={() => router.push('/(app)/notifications')} divider />
          <AccountRow title={SIMPLE.account.files} tone="green" onPress={() => router.push('/(app)/documents')} divider />
          {(role === 'landlord' || role === 'property_manager') && (
            <>
              <AccountRow title="Room listings" tone="indigo" onPress={() => router.push('/(app)/(tabs)/listings')} divider />
              <AccountRow title="Property checks" tone="blue" onPress={() => router.push('/(app)/(tabs)/compliance')} divider />
            </>
          )}
          {role === 'tenant' && (
            <>
              <AccountRow title="My home" tone="blue" onPress={() => router.push('/(app)/(tabs)/tenancy')} divider />
              <AccountRow title="Find a room" tone="indigo" onPress={() => router.push('/(app)/(tabs)/find')} divider />
              <AccountRow title="Saved rooms" tone="amber" onPress={() => router.push('/(app)/wishlist')} divider />
            </>
          )}
          {showCompliance && role !== 'landlord' && role !== 'property_manager' ? (
            <AccountRow title="Property checks" tone="blue" onPress={() => router.push('/(app)/(tabs)/compliance')} divider />
          ) : null}
          {role === 'property_manager' ? (
            <AccountRow title="Inspections" tone="indigo" onPress={() => router.push('/(app)/(tabs)/inspections')} divider />
          ) : null}
          <AccountRow title={SIMPLE.account.password} tone="indigo" onPress={() => router.push('/(app)/security')} />
        </Card>
      </Section>

      <Section title="Settings">
        <Card padded={false}>
          <AccountRow
            title={SIMPLE.account.help}
            tone="blue"
            onPress={() => Linking.openURL(BIRMINGHAM_COUNCIL.housingStandardsUrl)}
            divider
          />
          <AccountRow title={SIMPLE.account.signOut} tone="red" danger onPress={() => void handleSignOut()} />
        </Card>
      </Section>
    </Screen>
  );
}

const styles = StyleSheet.create({
  pageTitle: {
    fontSize: 28,
    fontFamily: FONT_BOLD,
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
    letterSpacing: -0.5,
  },
  profile: { marginBottom: theme.spacing.md },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  profileCopy: { flex: 1, minWidth: 0, gap: 4 },
  name: { fontSize: 18, fontFamily: FONT_SEMIBOLD, color: theme.colors.text },
  email: { fontSize: 14, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
});

export default function MoreScreen() {
  const { hmore, user } = useAuth();
  if (staffShellActive(user?.role, !!hmore)) return <StaffMore />;
  if (hmore) return <HmoreAccount />;
  return <LegacyMoreScreen />;
}
