import { router } from 'expo-router';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { useOfflineDrafts } from '@/hooks/useStaffDrafts';
import type { OfflineDraft } from '@/lib/hmore/offline/store';

const STATUS_LABEL: Record<OfflineDraft['syncState'], string> = {
  draft: 'Draft',
  pending: 'Waiting to sync',
  syncing: 'Syncing',
  synced: 'Synced',
  failed: 'Failed',
  conflict: 'Conflict',
  needs_attention: 'Needs attention',
};

const TYPE_LABEL: Record<OfflineDraft['type'], string> = {
  daily_log: 'Daily note',
  visit_update: 'Visit update',
  task_update: 'Task update',
  work_order_update: 'Work order',
  repair_create: 'Repair',
};

function draftTitle(draft: OfflineDraft): string {
  const summary = draft.payload.summary ?? draft.payload.title ?? draft.payload.status;
  const name = typeof summary === 'string' && summary.trim() ? summary.trim() : TYPE_LABEL[draft.type];
  return name;
}

export function draftHref(draft: OfflineDraft): string | null {
  if (draft.type === 'daily_log') return '/(app)/(tabs)/notes';
  if (draft.type === 'visit_update' && typeof draft.payload.visit_id === 'string') {
    return `/(app)/staff/visits?visitId=${draft.payload.visit_id}`;
  }
  if (draft.type === 'task_update' && typeof draft.payload.task_id === 'string') {
    return `/(app)/staff/tasks?taskId=${draft.payload.task_id}`;
  }
  if (draft.type === 'work_order_update' && typeof draft.payload.request_id === 'string') {
    return `/(app)/staff/work-order/${draft.payload.request_id}`;
  }
  if (draft.type === 'repair_create' && draft.serverResourceId) return `/(app)/maintenance/${draft.serverResourceId}`;
  if (draft.type === 'repair_create') return '/(app)/maintenance/new';
  return null;
}

export function OfflineDraftsScreen() {
  const drafts = useOfflineDrafts();
  const [note, setNote] = useState('');

  async function sync() {
    const report = await drafts.syncNow();
    if (report.offline) {
      setNote('Still offline or the connection is unstable. Nothing was sent.');
      return;
    }
    const saved = report.results.filter((item) => item.saved).length;
    const kept = report.results.filter((item) => !item.saved).length;
    setNote(kept ? `${saved} saved on the server. ${kept} still on this device.` : saved ? `${saved} saved on the server.` : 'No drafts waiting to sync.');
  }

  async function retryFailed() {
    const report = await drafts.retryFailed();
    if (report.offline) {
      setNote('Still offline. Failed drafts were kept.');
      return;
    }
    const saved = report.results.filter((item) => item.saved).length;
    setNote(saved ? `${saved} failed draft${saved === 1 ? '' : 's'} saved on the server.` : 'No failed draft was accepted.');
  }

  return (
    <StaffPage
      title="Offline drafts"
      subtitle="Sync Now sends waiting drafts. A draft stays here until the server accepts it. This app does not sync continuously in the background."
    >
      <Button title="Sync now" onPress={() => void sync()} loading={drafts.syncing} fullWidth />
      <Button title="Retry failed" variant="outline" onPress={() => void retryFailed()} fullWidth />
      {note ? <Feedback text={note} tone={note.includes('still') || note.includes('offline') || note.includes('No failed') ? 'warn' : 'ok'} /> : null}
      {drafts.drafts.length === 0 ? <RecordCard title="No drafts" detail="Saved notes, visits, tasks, work orders, and repairs appear here." /> : null}
      {drafts.drafts.map((draft) => {
        const href = draftHref(draft);
        return (
          <RecordCard
            key={draft.id}
            title={draftTitle(draft)}
            status={STATUS_LABEL[draft.syncState]}
            detail={[TYPE_LABEL[draft.type], draft.lastError].filter(Boolean).join(' · ')}
            onPress={href ? () => router.push(href as never) : undefined}
          />
        );
      })}
    </StaffPage>
  );
}
