import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';

import { ChoiceRow, DraftBadge, Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { useAuth } from '@/contexts/AuthContext';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { isDeviceOnline, pingHmoreHealth } from '@/lib/hmore/staff/network';
import { listOwnTasks, updateTask } from '@/lib/hmore/services/staff/tasks';

const STATUSES = ['open', 'in_progress', 'blocked', 'completed', 'cancelled'];

export function TaskBoard() {
  const { user } = useAuth();
  const params = useLocalSearchParams<{ taskId?: string }>();
  const drafts = useStaffDrafts();
  const query = useQuery({
    queryKey: ['hmore', 'staff', 'tasks', user?.id],
    queryFn: () => listOwnTasks(user?.id || ''),
    enabled: !!user?.id,
  });
  const [selected, setSelected] = useState(params.taskId || '');
  const [status, setStatus] = useState('in_progress');
  const [feedback, setFeedback] = useState('');
  const [savedOnServer, setSavedOnServer] = useState(false);
  const [busy, setBusy] = useState(false);

  if (query.isLoading) return <LoadingScreen message="Loading tasks..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load tasks')} onRetry={query.refetch} />;

  const tasks = query.data?.items ?? [];
  const current = tasks.find((task) => task.id === (selected || tasks[0]?.id)) ?? tasks[0];

  async function save() {
    if (!current) return;
    const payload = { task_id: current.id, status };
    setBusy(true);
    setSavedOnServer(false);
    try {
      const online = await isDeviceOnline({ ping: pingHmoreHealth });
      if (!online) {
        await drafts.save({ type: 'task_update', payload });
        setFeedback('Saved on this device. It is not on the server yet.');
        return;
      }
      const updated = await updateTask(current.id, { status });
      setSavedOnServer(true);
      setFeedback(`Server status: ${updated.status}`);
      const existing = drafts.drafts.find((draft) => draft.payload.task_id === current.id);
      if (existing) await drafts.remove(existing.id);
      await query.refetch();
    } catch (error) {
      await drafts.save({ type: 'task_update', payload });
      setFeedback(`${hmoreErrorMessage(error)} The update is still a draft.`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <StaffPage title="Tasks" subtitle="Assigned tasks. The status label is the one returned by the server." onRefresh={query.refetch} refreshing={query.isRefetching}>
      <DraftBadge count={drafts.drafts.filter((draft) => draft.type === 'task_update').length} />
      {tasks.length === 0 ? <RecordCard title="No tasks" detail="No assigned tasks were returned." /> : null}
      {tasks.map((task) => (
        <RecordCard
          key={task.id}
          title={task.title}
          status={task.overdue ? `${task.status} · overdue` : task.status}
          detail={task.description}
          onPress={() => setSelected(task.id)}
        />
      ))}
      {current ? (
        <>
          <ChoiceRow value={status} onChange={setStatus} options={STATUSES.map((item) => ({ id: item, label: item.replace(/_/g, ' ') }))} />
          <Button title="Update task" onPress={save} loading={busy} fullWidth />
          {feedback ? <Feedback text={feedback} tone={savedOnServer ? 'ok' : 'warn'} /> : null}
        </>
      ) : null}
    </StaffPage>
  );
}
