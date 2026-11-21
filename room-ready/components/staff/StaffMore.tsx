import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { PushPreferenceToggle } from '@/components/PushPreferenceToggle';
import { DeviceSecurityPanel } from '@/components/security/DeviceSecurityPanel';
import { DraftBadge, StaffPage } from '@/components/staff/ui';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Avatar, ListRow } from '@/components/ui/ListRow';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hasPermission, isSupportShellRole } from '@/lib/hmore/roles';
import { ROLE_LABELS } from '@/types';

type Row = {
  key: string;
  title: string;
  detail?: string;
  icon: keyof typeof Ionicons.glyphMap;
  href?:
    | '/(app)/offline-drafts'
    | '/(app)/notifications'
    | '/(app)/documents'
    | '/(app)/security'
    | '/(app)/(tabs)/schedule'
    | '/(app)/staff/visits'
    | '/(app)/staff/handovers'
    | '/(app)/staff/tasks'
    | '/(app)/staff/incidents'
    | '/(app)/staff/occupancy'
    | '/(app)/staff/approvals';
};

export function StaffMore() {
  const { user, hmore, signOut } = useAuth();
  const drafts = useStaffDrafts();
  const support = isSupportShellRole(user?.role);
  const canReview = hasPermission(hmore?.rbac.permissions, 'approvals.inbox.read');
  const name = `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim() || 'Account';

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/welcome');
  }

  const work: Row[] = [];
  if (user?.role === 'contractor') {
    work.push(
      { key: 'documents', title: 'Documents', icon: 'folder-outline', href: '/(app)/documents' },
      { key: 'schedule', title: 'Schedule', icon: 'calendar-outline', href: '/(app)/(tabs)/schedule' },
    );
  }
  if (support) {
    work.push(
      { key: 'visits', title: 'Visits', icon: 'walk-outline', href: '/(app)/staff/visits' },
      { key: 'handovers', title: 'Handovers', icon: 'swap-horizontal-outline', href: '/(app)/staff/handovers' },
      { key: 'tasks', title: 'Tasks', icon: 'checkbox-outline', href: '/(app)/staff/tasks' },
      { key: 'incidents', title: 'Incidents', icon: 'alert-circle-outline', href: '/(app)/staff/incidents' },
      { key: 'occupancy', title: 'Occupancy surveys', detail: 'Surveys only. No live camera counts.', icon: 'business-outline', href: '/(app)/staff/occupancy' },
    );
    if (canReview) {
      work.push({ key: 'approvals', title: 'Approvals', detail: 'Supervisor inbox', icon: 'checkmark-circle-outline', href: '/(app)/staff/approvals' });
    }
  }

  const settings: Row[] = [
    {
      key: 'drafts',
      title: 'Offline drafts',
      detail: drafts.count ? `${drafts.count} on this device` : 'Sync now, or retry a failed draft',
      icon: 'cloud-offline-outline',
      href: '/(app)/offline-drafts',
    },
    { key: 'alerts', title: 'Notifications', detail: 'In-app alerts', icon: 'notifications-outline', href: '/(app)/notifications' },
    { key: 'privacy', title: 'Privacy and security', icon: 'lock-closed-outline', href: '/(app)/security' },
  ];

  return (
    <StaffPage title="Account" subtitle="Profile and the rest of the staff tools. Super admin web tools are not in this app.">
      <Card style={styles.profile}>
        <View style={styles.profileRow}>
          <Avatar name={name} />
          <View style={styles.profileCopy}>
            <Text style={styles.name} numberOfLines={1}>{name}</Text>
            <Text style={styles.email} numberOfLines={1}>{user?.email}</Text>
            {user?.role ? <Chip label={ROLE_LABELS[user.role]} tone="blue" style={styles.role} /> : null}
          </View>
        </View>
      </Card>
      <DraftBadge count={drafts.count} />
      {work.length ? (
        <>
          <Text style={styles.section}>Work</Text>
          <Card padded={false} style={styles.group}>
            {work.map((row, index) => (
              <ListRow
                key={row.key}
                title={row.title}
                subtitle={row.detail}
                icon={row.icon}
                divider={index < work.length - 1}
                onPress={row.href ? () => router.push(row.href!) : undefined}
              />
            ))}
          </Card>
        </>
      ) : null}
      {user?.role === 'organisation_admin' ? (
        <Card style={styles.note}>
          <Text style={styles.noteTitle}>Organisation tools</Text>
          <Text style={styles.noteBody}>Approvals and caseload are in this app. Platform administration stays on the web.</Text>
        </Card>
      ) : null}
      <Text style={styles.section}>Settings</Text>
      <Card padded={false} style={styles.group}>
        {settings.map((row, index) => (
          <ListRow
            key={row.key}
            title={row.title}
            subtitle={row.detail}
            icon={row.icon}
            divider={index < settings.length - 1}
            onPress={row.href ? () => router.push(row.href!) : undefined}
          />
        ))}
      </Card>
      <DeviceSecurityPanel onSignedOut={() => router.replace('/(auth)/welcome')} />
      <PushPreferenceToggle />
      <Text style={styles.section}>Account</Text>
      <Card padded={false} style={styles.group}>
        <ListRow title="Sign out" icon="log-out-outline" tone="red" onPress={handleSignOut} />
      </Card>
    </StaffPage>
  );
}

const styles = StyleSheet.create({
  profile: { marginBottom: theme.spacing.md },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  profileCopy: { flex: 1, minWidth: 0, gap: 4 },
  name: { fontFamily: FONT_SEMIBOLD, fontSize: 18, color: theme.colors.text },
  email: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  role: { marginTop: 4 },
  section: {
    fontFamily: FONT_SEMIBOLD,
    fontSize: 13,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: theme.colors.textMuted,
    marginBottom: 8,
  },
  group: { marginBottom: theme.spacing.md },
  note: { marginBottom: theme.spacing.md },
  noteTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text },
  noteBody: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4, lineHeight: 20 },
});
