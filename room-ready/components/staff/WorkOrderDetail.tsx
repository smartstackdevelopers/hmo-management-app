import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';

import { DraftBadge, Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { isDeviceOnline, pingHmoreHealth } from '@/lib/hmore/staff/network';
import { getMaintenance } from '@/lib/hmore/services/maintenance';
import { completeWorkOrder, listWorkOrderVisits, updateWorkOrderStatus } from '@/lib/hmore/services/staff/workOrders';

export function WorkOrderDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const client = useQueryClient();
  const drafts = useStaffDrafts();
  const order = useQuery({
    queryKey: ['hmore', 'staff', 'work-order', id],
    queryFn: () => getMaintenance(id),
    enabled: !!id,
  });
  const visits = useQuery({
    queryKey: ['hmore', 'staff', 'work-order-visits', id],
    queryFn: () => listWorkOrderVisits(id),
    enabled: !!id,
  });
  const [notes, setNotes] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);

  if (order.isLoading) return <LoadingScreen message="Loading work order..." />;
  if (order.isError || !order.data) {
    return <ErrorState message={hmoreErrorMessage(order.error, 'Could not load this work order')} onRetry={order.refetch} />;
  }

  const row = order.data;

  async function run(action: 'in_progress' | 'on_hold' | 'complete') {
    const payload = {
      request_id: row.id,
      action: action === 'complete' ? 'complete' : 'transition',
      status: action === 'complete' ? undefined : action,
      note: notes.trim(),
      work_notes: notes.trim(),
    };
    setBusy(true);
    setFeedback('');
    try {
      const online = await isDeviceOnline({ ping: pingHmoreHealth });
      if (!online) {
        await drafts.save({ type: 'work_order_update', payload });
        setFeedback('Saved on this device. It is not on the server yet.');
        return;
      }
      if (action === 'complete' && !notes.trim()) {
        setFeedback('Completion needs work notes. Nothing was sent.');
        return;
      }
      const updated = action === 'complete'
        ? await completeWorkOrder(row.id, notes.trim())
        : await updateWorkOrderStatus(row.id, action, notes.trim() || undefined);
      const confirmed = await getMaintenance(updated.id);
      setFeedback(`Server status: ${confirmed.status}. Approval: ${confirmed.approval_status ?? 'none'}.`);
      const existing = drafts.drafts.find((draft) => draft.payload.request_id === row.id);
      if (existing) await drafts.remove(existing.id);
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-order', id] });
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-orders'] });
    } catch (error) {
      await drafts.save({ type: 'work_order_update', payload });
      setFeedback(`${hmoreErrorMessage(error)} The change is still a draft.`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <StaffPage title={row.reference_number} subtitle={row.title} onRefresh={order.refetch} refreshing={order.isRefetching}>
      <DraftBadge count={drafts.drafts.filter((draft) => draft.payload.request_id === row.id).length} />
      <RecordCard title="Status" status={row.status} detail={`Approval: ${row.approval_status ?? 'none'}`} />
      <RecordCard title="Priority" detail={row.priority} />
      {row.scheduled_visit_at ? <RecordCard title="Scheduled" detail={formatUKDate(row.scheduled_visit_at)} /> : null}
      {(visits.data ?? []).map((visit) => (
        <RecordCard key={visit.id} title="Visit" status={visit.status} detail={formatUKDate(visit.scheduled_at)} />
      ))}
      <Input label="Work notes" value={notes} onChangeText={setNotes} multiline />
      <Button title="Mark in progress" onPress={() => run('in_progress')} loading={busy} fullWidth />
      <Button title="Put on hold" variant="outline" onPress={() => run('on_hold')} fullWidth />
      <Button title="Complete" variant="outline" onPress={() => run('complete')} disabled={!notes.trim()} fullWidth />
      {feedback ? <Feedback text={feedback} tone={feedback.startsWith('Server status') ? 'ok' : 'warn'} /> : null}
    </StaffPage>
  );
}
