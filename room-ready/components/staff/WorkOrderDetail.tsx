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
import { retainAttachment } from '@/lib/hmore/offline/attachments';
import { getMaintenance } from '@/lib/hmore/services/maintenance';
import { listWorkOrderVisits } from '@/lib/hmore/services/staff/workOrders';
import { pickImage } from '@/lib/uploads';

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
  const [photos, setPhotos] = useState<{ uri: string; name: string; mimeType: string }[]>([]);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);

  if (order.isLoading) return <LoadingScreen message="Loading work order..." />;
  if (order.isError || !order.data) {
    return <ErrorState message={hmoreErrorMessage(order.error, 'Could not load this work order')} onRetry={order.refetch} />;
  }

  const row = order.data;

  async function addPhoto() {
    const image = await pickImage();
    if (!image) return;
    setPhotos((current) => [
      ...current,
      { uri: image.uri, name: image.fileName || 'work-order.jpg', mimeType: image.mimeType || 'image/jpeg' },
    ]);
  }

  async function run(action: 'in_progress' | 'on_hold' | 'complete') {
    if (action === 'complete' && !notes.trim()) {
      setFeedback('Completion needs work notes. Nothing was sent.');
      return;
    }
    const stored = [];
    for (const photo of photos) {
      const uri = drafts.owner ? await retainAttachment(drafts.owner, photo.uri, row.id, undefined, photo.name) : photo.uri;
      stored.push({ ...photo, uri });
    }
    const payload = {
      request_id: row.id,
      action: action === 'complete' ? 'complete' : 'transition',
      status: action === 'complete' ? undefined : action,
      note: notes.trim(),
      work_notes: notes.trim(),
      if_match_updated_at: row.updated_at,
      local_files: stored,
    };
    setBusy(true);
    setFeedback('');
    try {
      const draft = await drafts.save({
        type: 'work_order_update',
        payload,
        localAttachmentUris: stored.map((photo) => photo.uri),
        serverUpdatedAt: row.updated_at,
      });
      const online = await isDeviceOnline({ ping: pingHmoreHealth });
      if (!online) {
        setFeedback('Saved on this device. It is not on the server yet.');
        return;
      }
      const report = await drafts.sync();
      const result = report.results.find((item) => item.id === draft.id);
      if (!result?.saved) {
        setFeedback(`${result?.error || 'The change was not confirmed.'} The change is still a draft.`);
        return;
      }
      const confirmed = await getMaintenance(row.id);
      setFeedback(`Server status: ${confirmed.status}. Approval: ${confirmed.approval_status ?? 'none'}.`);
      setPhotos([]);
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-order', id] });
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'work-orders'] });
    } catch (error) {
      setFeedback(`${hmoreErrorMessage(error)} The change is still a draft.`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <StaffPage title={row.reference_number} subtitle={row.title} onRefresh={order.refetch} refreshing={order.isRefetching}>
      <DraftBadge count={drafts.drafts.filter((draft) => draft.payload.request_id === row.id).length} />
      {drafts.drafts.filter((draft) => draft.payload.request_id === row.id && draft.lastError).map((draft) => (
        <Feedback key={draft.id} text={draft.lastError || ''} tone="warn" />
      ))}
      <RecordCard title="Status" status={row.status} detail={`Approval: ${row.approval_status ?? 'none'}`} />
      <RecordCard title="Priority" detail={row.priority} />
      {row.scheduled_visit_at ? <RecordCard title="Scheduled" detail={formatUKDate(row.scheduled_visit_at)} /> : null}
      {(visits.data ?? []).map((visit) => (
        <RecordCard key={visit.id} title="Visit" status={visit.status} detail={formatUKDate(visit.scheduled_at)} />
      ))}
      <Input label="Work notes" value={notes} onChangeText={setNotes} multiline />
      <Button title="Add photo" variant="outline" onPress={() => void addPhoto()} fullWidth />
      {photos.map((photo) => (
        <RecordCard key={photo.uri} title={photo.name} detail="Photo stays on this device until the upload is confirmed." />
      ))}
      <Button title="Mark in progress" onPress={() => run('in_progress')} loading={busy} fullWidth />
      <Button title="Put on hold" variant="outline" onPress={() => run('on_hold')} fullWidth />
      <Button title="Complete" variant="outline" onPress={() => run('complete')} disabled={!notes.trim()} fullWidth />
      {feedback ? <Feedback text={feedback} tone={feedback.startsWith('Server status') ? 'ok' : 'warn'} /> : null}
    </StaffPage>
  );
}
