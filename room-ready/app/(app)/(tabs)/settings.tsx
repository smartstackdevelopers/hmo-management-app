import { router } from 'expo-router';
import { Text, View } from 'react-native';

import { InitialsTile, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { ListRow } from '@/components/ui/ListRow';
import { Screen } from '@/components/ui/Screen';
import { Section } from '@/components/ui/Section';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { ROLE_LABELS } from '@/types';

export default function SettingsScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(TAB_ROLES.settings);
  const { user, signOut } = useAuth();

  if (guard) return guard;

  const name = `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim() || 'Account';

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/welcome');
  }

  return (
    <Screen>
      <Text accessibilityRole="header" style={{ fontFamily: FONT_BOLD, fontSize: 28, color: theme.colors.text, letterSpacing: -0.4 }}>
        Platform
      </Text>
      <Card style={{ marginTop: 12, marginBottom: 16 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <InitialsTile name={name} size={48} />
          <View style={{ flex: 1, minWidth: 0 }}>
            <Text style={{ fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text }} numberOfLines={1}>{name}</Text>
            {user?.email ? <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 }} numberOfLines={1}>{user.email}</Text> : null}
            {user?.role ? <Chip label={ROLE_LABELS[user.role]} tone="blue" style={{ marginTop: 6 }} /> : null}
          </View>
        </View>
      </Card>
      <Section title="Platform">
        <Card padded={false}>
          <ListRow title="Users" icon="people-outline" onPress={() => router.push('/(app)/(tabs)/users')} />
        </Card>
      </Section>
      <Section title="Account">
        <Card padded={false}>
          <ListRow title="Sign out" icon="log-out-outline" tone="red" onPress={handleSignOut} />
        </Card>
      </Section>
    </Screen>
  );
}
