import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import {
  completeMaintenanceVisit,
  scheduleMaintenanceVisit,
} from '@/lib/hmore/services/maintenance';
import { listAssignedWorkOrders, listWorkOrderVisits } from '@/lib/hmore/services/staff/workOrders';

export function ContractorSchedule() {
  const client = useQueryClient();
  const orders = useQuery({ queryKey: ['hmore', 'staff', 'work-orders'], queryFn: listAssignedWorkOrders });
  const [requestId, setRequestId] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [workNotes, setWorkNotes] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const selected = requestId || orders.data?.items[0]?.id || '';
  const visits = useQuery({
    queryKey: ['hmore', 'staff', 'work-order-visits', selected],
    queryFn: () => listWorkOrderVisits(selected),
    enabled: !!selected,
  });

  if (orders.isLoading) return <LoadingScreen message="Loading schedule..." />;
  if (orders.isError) return <ErrorState message={hmoreErrorMessage(orders.error, 'Could not load work orders')} onRetry={orders.refetch} />;

  async function schedule() {
    if (!selected || !date || !time) {
      setFeedback('Choose a work order and enter a date and time. Nothing was sent.');
      return;
    }
    const local = new Date(`${date}T${time}:00`);
    if (Number.isNaN(local.getTime())) {
      setFeedback('Enter the date as YYYY-MM-DD and the time as HH:MM.');
      return;
    }
    setBusy(true);
    try {
      const created = await scheduleMaintenanceVisit(selected, { scheduled_at: local.toISOString(), timezone: 'Europe/London' });
      setFeedback(`Visit saved. Server status: ${created.status}.`);
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-order-visits', selected] });
    } catch (error) {
      setFeedback(hmoreErrorMessage(error, 'The visit was not saved.'));
    } finally {
      setBusy(false);
    }
  }

  async function complete(visitId: string) {
    if (!workNotes.trim()) {
      setFeedback('Enter work notes before completing a visit. Nothing was sent.');
      return;
    }
    setBusy(true);
    try {
      const updated = await completeMaintenanceVisit(selected, visitId, { work_notes: workNotes.trim() });
      setFeedback(`Visit updated. Server status: ${updated.status}.`);
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-order-visits', selected] });
    } catch (error) {
      setFeedback(hmoreErrorMessage(error, 'The visit was not updated.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <StaffPage title="Schedule" subtitle="Visits for work orders assigned to you. Status text is the server status." onRefresh={orders.refetch} refreshing={orders.isRefetching}>
      {(orders.data?.items ?? []).map((order) => (
        <RecordCard
          key={order.id}
          title={order.title}
          status={order.status}
          detail={order.scheduled_visit_at ? formatUKDate(order.scheduled_visit_at) : order.reference_number}
          onPress={() => setRequestId(order.id)}
        />
      ))}
      {(orders.data?.items ?? []).length === 0 ? <RecordCard title="No work orders" detail="There is nothing to schedule." /> : null}
      <Input label="Work notes for completion" value={workNotes} onChangeText={setWorkNotes} />
      <Input label="Date (YYYY-MM-DD)" value={date} onChangeText={setDate} autoCapitalize="none" />
      <Input label="Time (HH:MM)" value={time} onChangeText={setTime} autoCapitalize="none" />
      <Button title="Schedule visit" onPress={schedule} loading={busy} disabled={!selected} fullWidth />
      {(visits.data ?? []).map((visit) => (
        <RecordCard
          key={visit.id}
          title={formatUKDate(visit.scheduled_at)}
          status={visit.status}
          detail="Complete sends these work notes and then shows the server status."
          onPress={() => complete(visit.id)}
        />
      ))}
      {feedback ? <Feedback text={feedback} tone={feedback.includes('Server status') || feedback.includes('Visit saved') || feedback.includes('Visit updated') ? 'ok' : 'warn'} /> : null}
    </StaffPage>
  );
}
