import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { DraftBadge, Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/contexts/AuthContext';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hasPermission, isSupportShellRole } from '@/lib/hmore/roles';
import { ROLE_LABELS } from '@/types';

export function StaffHome() {
  const { user, hmore } = useAuth();
  const drafts = useStaffDrafts();
  const [syncNote, setSyncNote] = useState('');
  const support = isSupportShellRole(user?.role);
  const canReview = hasPermission(hmore?.rbac.permissions, 'approvals.inbox.read');
  const role = user?.role ? ROLE_LABELS[user.role] : 'Staff';

  async function sync() {
    const report = await drafts.sync();
    if (report.offline) {
      setSyncNote('Still offline. Drafts were not sent.');
      return;
    }
    const saved = report.results.filter((item) => item.saved).length;
    const kept = report.results.filter((item) => !item.saved).length;
    setSyncNote(
      kept
        ? `${saved} saved on the server. ${kept} still on this device.`
        : saved
          ? `${saved} saved on the server.`
          : 'No drafts to send.',
    );
  }

  return (
    <StaffPage
      title={support ? 'Support' : 'Jobs'}
      subtitle={`${role}. Records come from HMore. A draft stays on this device until the server accepts it.`}
    >
      <DraftBadge count={drafts.count} />
      {drafts.count > 0 ? <Button title="Sync drafts" onPress={sync} variant="outline" fullWidth /> : null}
      {syncNote ? <Feedback text={syncNote} tone={syncNote.includes('still') || syncNote.includes('offline') ? 'warn' : 'ok'} /> : null}
      <View style={{ height: 12 }} />
      {support ? (
        <>
          <RecordCard title="My tenants" detail="Assigned caseload" onPress={() => router.push('/(app)/(tabs)/caseload')} />
          <RecordCard title="Shifts" detail="Your rota" onPress={() => router.push('/(app)/(tabs)/shifts')} />
          <RecordCard title="Notes" detail="Daily logs, with device dictation" onPress={() => router.push('/(app)/(tabs)/notes')} />
          <RecordCard title="Visits" detail="Assigned visits" onPress={() => router.push('/(app)/staff/visits')} />
          <RecordCard title="Tasks" detail="Assigned tasks" onPress={() => router.push('/(app)/staff/tasks')} />
          <RecordCard title="Incidents" detail="Create and review incident reports" onPress={() => router.push('/(app)/staff/incidents')} />
          <RecordCard
            title="Occupancy surveys"
            detail="Site surveys only. Live camera counts are Phase 6 and are not shown."
            onPress={() => router.push('/(app)/staff/occupancy')}
          />
          {canReview ? (
            <RecordCard title="Approvals" detail="Inbox status comes from the server" onPress={() => router.push('/(app)/staff/approvals')} />
          ) : null}
        </>
      ) : (
        <>
          <RecordCard title="Work orders" detail="Maintenance assigned to you" onPress={() => router.push('/(app)/(tabs)/work-orders')} />
          <RecordCard title="Scheduling" detail="Visits on those work orders" onPress={() => router.push('/(app)/(tabs)/schedule')} />
          <RecordCard title="Photo evidence" detail="Upload a completion photo" onPress={() => router.push('/(app)/(tabs)/evidence')} />
        </>
      )}
      <RecordCard title="Notifications" detail="In-app messages. Device push is not registered." onPress={() => router.push('/(app)/notifications')} />
    </StaffPage>
  );
}
