import { router } from 'expo-router';
import { Text } from 'react-native';

import { PushPreferenceToggle } from '@/components/PushPreferenceToggle';
import { DeviceSecurityPanel } from '@/components/security/DeviceSecurityPanel';
import { DraftBadge, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Avatar } from '@/components/ui/ListRow';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hasPermission, isSupportShellRole } from '@/lib/hmore/roles';
import { ROLE_LABELS } from '@/types';

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

  return (
    <StaffPage title="Account" subtitle="Profile and the rest of the staff tools. Super admin web tools are not in this app.">
      <Card>
        <Avatar name={name} />
        <Text style={{ fontFamily: FONT_SEMIBOLD, fontSize: 18, color: theme.colors.text, marginTop: 8 }}>{name}</Text>
        <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 }}>{user?.email}</Text>
        {user?.role ? (
          <Text style={{ fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, marginTop: 8 }}>{ROLE_LABELS[user.role]}</Text>
        ) : null}
      </Card>
      <DraftBadge count={drafts.count} />
      <RecordCard
        title="Offline drafts"
        detail={drafts.count ? `${drafts.count} on this device` : 'Sync now, or retry a failed draft'}
        onPress={() => router.push('/(app)/offline-drafts')}
      />
      <RecordCard title="Notifications" detail="In-app alerts" onPress={() => router.push('/(app)/notifications')} />
      {support ? (
        <>
          <RecordCard title="Visits" onPress={() => router.push('/(app)/staff/visits')} />
          <RecordCard title="Tasks" onPress={() => router.push('/(app)/staff/tasks')} />
          <RecordCard title="Incidents" onPress={() => router.push('/(app)/staff/incidents')} />
          <RecordCard title="Occupancy surveys" detail="Surveys only. No live camera counts." onPress={() => router.push('/(app)/staff/occupancy')} />
          {canReview ? <RecordCard title="Approvals" detail="Supervisor inbox" onPress={() => router.push('/(app)/staff/approvals')} /> : null}
        </>
      ) : null}
      {user?.role === 'organisation_admin' ? (
        <RecordCard title="Organisation tools" detail="Approvals and caseload are in this app. Platform administration stays on the web." />
      ) : null}
      <DeviceSecurityPanel onSignedOut={() => router.replace('/(auth)/welcome')} />
      <PushPreferenceToggle />
      <Button title="Sign out" variant="outline" onPress={handleSignOut} fullWidth />
    </StaffPage>
  );
}
