import { useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Text } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { AgendaRow, Feedback, StaffPage, StatusRow, WeekStrip, staffLabel, statusTone } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { completeMaintenanceVisit, scheduleMaintenanceVisit } from '@/lib/hmore/services/maintenance';
import { listAssignedWorkOrders, listWorkOrderVisits } from '@/lib/hmore/services/staff/workOrders';
import type { MaintenanceRequest } from '@/lib/hmore/types';

function startOfWeek(now = new Date()): Date {
  const day = now.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + mondayOffset);
  start.setHours(0, 0, 0, 0);
  return start;
}

function dayKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

function sameDay(iso: string | null | undefined, day: Date): boolean {
  if (!iso) return false;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return false;
  return date.getFullYear() === day.getFullYear() && date.getMonth() === day.getMonth() && date.getDate() === day.getDate();
}

function clock(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

export function ContractorSchedule() {
  useHideTabHeader();
  const client = useQueryClient();
  const orders = useQuery({ queryKey: ['hmore', 'staff', 'work-orders'], queryFn: listAssignedWorkOrders });
  const weekStart = useMemo(() => startOfWeek(), []);
  const days = useMemo(
    () =>
      Array.from({ length: 7 }, (_, index) => {
        const date = new Date(weekStart);
        date.setDate(weekStart.getDate() + index);
        return date;
      }),
    [weekStart],
  );
  const [selectedKey, setSelectedKey] = useState(() => dayKey(new Date()));
  const [requestId, setRequestId] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [workNotes, setWorkNotes] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const selectedId = requestId || orders.data?.items[0]?.id || '';
  const visits = useQuery({
    queryKey: ['hmore', 'staff', 'work-order-visits', selectedId],
    queryFn: () => listWorkOrderVisits(selectedId),
    enabled: !!selectedId,
  });

  if (orders.isLoading) return <LoadingScreen message="Loading schedule..." />;
  if (orders.isError) return <ErrorState message={hmoreErrorMessage(orders.error, 'Could not load work orders')} onRetry={orders.refetch} />;

  const jobs = orders.data?.items ?? [];
  const selected = days.find((day) => dayKey(day) === selectedKey) ?? days[0];
  const dayJobs = jobs.filter((job) => sameDay(job.scheduled_visit_at, selected));
  const unscheduled = jobs.filter((job) => !job.scheduled_visit_at);
  const weekJobs = jobs.filter((job) => {
    if (!job.scheduled_visit_at) return false;
    const when = new Date(job.scheduled_visit_at);
    const end = new Date(weekStart);
    end.setDate(end.getDate() + 7);
    return when >= weekStart && when < end;
  });

  async function schedule() {
    if (!selectedId || !date || !time) {
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
      const created = await scheduleMaintenanceVisit(selectedId, { scheduled_at: local.toISOString(), timezone: 'Europe/London' });
      setFeedback(`Visit saved. Server status: ${created.status}.`);
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-order-visits', selectedId] });
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-orders'] });
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
      const updated = await completeMaintenanceVisit(selectedId, visitId, { work_notes: workNotes.trim() });
      setFeedback(`Visit updated. Server status: ${updated.status}.`);
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-order-visits', selectedId] });
    } catch (error) {
      setFeedback(hmoreErrorMessage(error, 'The visit was not updated.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <StaffPage title="Schedule" subtitle={`${weekJobs.length} this week`} onRefresh={orders.refetch} refreshing={orders.isRefetching}>
      <WeekStrip
        selectedKey={dayKey(selected)}
        onSelect={setSelectedKey}
        days={days.map((day) => ({
          key: dayKey(day),
          weekday: day.toLocaleDateString('en-GB', { weekday: 'narrow' }),
          day: String(day.getDate()),
          marked: jobs.some((job) => sameDay(job.scheduled_visit_at, day)),
        }))}
      />
      {dayJobs.length === 0 ? (
        <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: 12 }}>
          No timed jobs on this day.
        </Text>
      ) : (
        dayJobs.map((job) => <JobRow key={job.id} job={job} onPress={() => router.push(`/(app)/staff/work-order/${job.id}`)} />)
      )}
      {dayKey(selected) === dayKey(new Date())
        ? unscheduled.map((job) => (
            <JobRow key={job.id} job={job} onPress={() => router.push(`/(app)/staff/work-order/${job.id}`)} />
          ))
        : null}
      <Input label="Date (YYYY-MM-DD)" value={date} onChangeText={setDate} autoCapitalize="none" />
      <Input label="Time (HH:MM)" value={time} onChangeText={setTime} autoCapitalize="none" />
      <Input label="Work notes for completion" value={workNotes} onChangeText={setWorkNotes} />
      <Button title="Schedule visit" onPress={schedule} loading={busy} disabled={!selectedId} fullWidth />
      {(visits.data ?? []).map((visit) => (
        <StatusRow
          key={visit.id}
          name={jobs.find((job) => job.id === selectedId)?.title || 'Visit'}
          title={formatUKDate(visit.scheduled_at)}
          subtitle={staffLabel(visit.status)}
          chip={staffLabel(visit.status)}
          tone={statusTone(visit.status)}
          onPress={() => complete(visit.id)}
        />
      ))}
      {feedback ? <Feedback text={feedback} tone={feedback.includes('status') || feedback.includes('saved') || feedback.includes('updated') ? 'ok' : 'warn'} /> : null}
    </StaffPage>
  );
}

function JobRow({ job, onPress }: { job: MaintenanceRequest; onPress: () => void }) {
  const urgent = job.priority === 'urgent' || job.priority === 'emergency' || job.priority === 'high';
  return (
    <AgendaRow
      time={clock(job.scheduled_visit_at)}
      title={job.title}
      subtitle={[job.reference_number, urgent ? staffLabel(job.priority) : null].filter(Boolean).join(' · ')}
      tone={urgent ? 'red' : statusTone(job.status)}
      onPress={onPress}
    />
  );
}
