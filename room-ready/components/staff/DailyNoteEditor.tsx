import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { ChoiceRow, DraftBadge, Feedback, RecordCard, StaffPage, staffLabel } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { useAuth } from '@/contexts/AuthContext';
import { useDeviceSpeechToText } from '@/hooks/useDeviceSpeechToText';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { isDeviceOnline, pingHmoreHealth } from '@/lib/hmore/staff/network';
import { listCaseload } from '@/lib/hmore/services/staff/caseload';
import { ACTIVITY_CATEGORIES, createDailyLog, listDailyLogs, type DailyLogInput } from '@/lib/hmore/services/staff/dailyLogs';

export function DailyNoteEditor() {
  const { user } = useAuth();
  const drafts = useStaffDrafts();
  const caseload = useQuery({
    queryKey: ['hmore', 'staff', 'caseload', user?.role],
    queryFn: () => listCaseload(user?.role, { page: 1, page_size: 50, status: 'active' }),
  });
  const logs = useQuery({
    queryKey: ['hmore', 'staff', 'daily-logs'],
    queryFn: () => listDailyLogs({ page: 1, page_size: 20 }),
  });
  const [tenantId, setTenantId] = useState('');
  const [category, setCategory] = useState<string>(ACTIVITY_CATEGORIES[0]);
  const [summary, setSummary] = useState('');
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [savedOnServer, setSavedOnServer] = useState(false);
  const speech = useDeviceSpeechToText((text) => {
    setNotes((current) => (current.trim() ? `${current.trim()} ${text}` : text));
    setSavedOnServer(false);
  });

  if (caseload.isLoading || logs.isLoading) return <LoadingScreen message="Loading notes..." />;
  if (caseload.isError) return <ErrorState message={hmoreErrorMessage(caseload.error, 'Could not load caseload')} onRetry={caseload.refetch} />;

  const tenants = caseload.data?.items ?? [];
  const selectedTenant = tenantId || tenants[0]?.tenant_id || '';

  async function save() {
    if (!selectedTenant || !summary.trim() || !notes.trim()) {
      setFeedback('Choose a tenant and enter a summary and note.');
      setSavedOnServer(false);
      return;
    }
    const payload: DailyLogInput = {
      tenant_id: selectedTenant,
      activity_category: category,
      summary: summary.trim(),
      notes: notes.trim(),
      follow_up_required: false,
    };
    setBusy(true);
    setSavedOnServer(false);
    try {
      const online = await isDeviceOnline({ ping: pingHmoreHealth });
      if (!online) {
        await drafts.save({ type: 'daily_log', payload: payload as unknown as Record<string, unknown> });
        setFeedback('Saved on this device. It is not on the server yet.');
        return;
      }
      const created = await createDailyLog(payload);
      if (!created?.id) throw new Error('The server did not confirm the note.');
      const existing = drafts.drafts.find((draft) => draft.type === 'daily_log' && draft.payload.tenant_id === selectedTenant);
      if (existing) await drafts.remove(existing.id);
      setSavedOnServer(true);
      setFeedback('Saved on the server.');
      setSummary('');
      setNotes('');
      await logs.refetch();
    } catch (error) {
      await drafts.save({ type: 'daily_log', payload: payload as unknown as Record<string, unknown> });
      setFeedback(`${hmoreErrorMessage(error, 'Could not save the note.')} The note is still a draft on this device.`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <StaffPage title="Notes" subtitle="Daily logs for your caseload. Dictation uses this device. It is not an AI rewrite." onRefresh={() => { logs.refetch(); caseload.refetch(); }} refreshing={logs.isRefetching}>
      <DraftBadge count={drafts.drafts.filter((draft) => draft.type === 'daily_log').length} />
      {tenants.length === 0 ? <RecordCard title="No tenants" detail="A note needs someone on your caseload." /> : (
        <ChoiceRow
          value={selectedTenant}
          onChange={setTenantId}
          options={tenants.map((item) => ({ id: item.tenant_id, label: item.tenant_preferred_name || item.tenant_full_name || 'Tenant' }))}
        />
      )}
      <ChoiceRow
        value={category}
        onChange={setCategory}
        options={ACTIVITY_CATEGORIES.map((item) => ({ id: item, label: staffLabel(item) }))}
      />
      <Input label="Summary" value={summary} onChangeText={setSummary} />
      <Input label="Note" value={notes} onChangeText={setNotes} multiline />
      {speech.interim ? <Feedback text={`Hearing: ${speech.interim}`} /> : null}
      {speech.message ? <Feedback text={speech.message} /> : null}
      <Button
        title={speech.listening ? 'Stop dictation' : 'Dictate'}
        variant="outline"
        onPress={speech.listening ? speech.stop : speech.start}
        fullWidth
      />
      <Button title="Save note" onPress={save} loading={busy} disabled={busy || tenants.length === 0} fullWidth />
      {feedback ? <Feedback text={feedback} tone={savedOnServer ? 'ok' : 'warn'} /> : null}
      {(logs.data?.items ?? []).map((log) => (
        <RecordCard key={log.id} title={log.summary} status={log.status} detail={`${log.log_date} · ${staffLabel(log.activity_category)}`} />
      ))}
      {logs.isError ? <Feedback text={hmoreErrorMessage(logs.error, 'Could not list notes.')} /> : null}
    </StaffPage>
  );
}
