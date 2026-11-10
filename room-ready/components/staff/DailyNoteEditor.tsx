import { useQuery } from '@tanstack/react-query';
import { useCallback, useRef, useState } from 'react';
import { Alert, Text } from 'react-native';

import { RewriteComparison } from '@/components/staff/voice/RewriteComparison';
import { ChoiceRow, DraftBadge, Feedback, RecordCard, StaffPage, staffLabel } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { useAuth } from '@/contexts/AuthContext';
import { useDeviceSpeechToText } from '@/hooks/useDeviceSpeechToText';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { isDeviceOnline, pingHmoreHealth } from '@/lib/hmore/staff/network';
import {
  applyFinalTranscript,
  canSubmitDailyLog,
  EMPTY_REWRITE_MESSAGE,
  rewriteFailureMessage,
  SAVE_CONFIRM_MESSAGE,
  textAfterAccept,
  textAfterReject,
} from '@/lib/hmore/staff/voiceNotes';
import { listCaseload } from '@/lib/hmore/services/staff/caseload';
import { reportIncorrectRewrite, rewriteDailyLogNote } from '@/lib/hmore/services/staff/dailyLogRewrite';
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
  const [reporting, setReporting] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [savedOnServer, setSavedOnServer] = useState(false);
  const [comparison, setComparison] = useState<{ original: string; activityId: string | null } | null>(null);
  const [editedRewritten, setEditedRewritten] = useState('');
  const editedRef = useRef(false);

  const onFinalText = useCallback((text: string) => {
    setNotes((current) => applyFinalTranscript({ current, transcript: text, userEdited: editedRef.current }).text);
    editedRef.current = false;
    setSavedOnServer(false);
  }, []);
  const speech = useDeviceSpeechToText(onFinalText);

  if (caseload.isLoading || logs.isLoading) return <LoadingScreen message="Loading notes..." />;
  if (caseload.isError) return <ErrorState message={hmoreErrorMessage(caseload.error, 'Could not load caseload')} onRetry={caseload.refetch} />;

  const tenants = caseload.data?.items ?? [];
  const selectedTenant = tenantId || tenants[0]?.tenant_id || '';

  function notePayload(): DailyLogInput | null {
    if (!selectedTenant || !summary.trim() || !notes.trim()) return null;
    return {
      tenant_id: selectedTenant,
      activity_category: category,
      summary: summary.trim(),
      notes: notes.trim(),
      follow_up_required: false,
    };
  }

  function onNotesChange(value: string) {
    editedRef.current = true;
    setNotes(value);
    setSavedOnServer(false);
  }

  async function saveDraft() {
    const payload = notePayload();
    if (!payload) {
      setFeedback('Choose a tenant and enter a summary and note.');
      setSavedOnServer(false);
      return;
    }
    setBusy(true);
    try {
      await drafts.save({ type: 'daily_log', payload: payload as unknown as Record<string, unknown> });
      setSavedOnServer(false);
      setFeedback('Saved on this device. It is not on the server yet.');
    } catch (error) {
      setSavedOnServer(false);
      setFeedback(hmoreErrorMessage(error, 'Could not save the draft on this device.'));
    } finally {
      setBusy(false);
    }
  }

  async function saveConfirmed() {
    if (!canSubmitDailyLog(true)) return;
    const payload = notePayload();
    if (!payload) {
      setFeedback('Choose a tenant and enter a summary and note.');
      setSavedOnServer(false);
      return;
    }
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
      editedRef.current = false;
      setComparison(null);
      await logs.refetch();
    } catch (error) {
      await drafts.save({ type: 'daily_log', payload: payload as unknown as Record<string, unknown> });
      setFeedback(`${hmoreErrorMessage(error, 'Could not save the note.')} The note is still a draft on this device.`);
    } finally {
      setBusy(false);
    }
  }

  function requestSave() {
    if (!notePayload()) {
      setFeedback('Choose a tenant and enter a summary and note.');
      setSavedOnServer(false);
      return;
    }
    if (!canSubmitDailyLog(false)) {
      Alert.alert('Save this note?', SAVE_CONFIRM_MESSAGE, [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Save note', onPress: () => void saveConfirmed() },
      ]);
    }
  }

  async function rewrite() {
    if (!notes.trim()) {
      setFeedback(EMPTY_REWRITE_MESSAGE);
      setSavedOnServer(false);
      return;
    }
    setBusy(true);
    setSavedOnServer(false);
    try {
      const result = await rewriteDailyLogNote({ text: notes, tenant_id: selectedTenant || null });
      setComparison({ original: notes, activityId: result.activity_id });
      setEditedRewritten(result.rewritten_text);
      setFeedback('Review the rewrite. Nothing is saved until you confirm.');
    } catch (error) {
      setFeedback(rewriteFailureMessage(error));
    } finally {
      setBusy(false);
    }
  }

  function acceptRewrite() {
    try {
      const next = textAfterAccept(editedRewritten);
      setNotes(next.notes);
      editedRef.current = true;
      setComparison(null);
      setSavedOnServer(false);
      setFeedback('The rewrite is in the note field. It is not saved until you confirm Save original note.');
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'The rewritten text is empty.');
    }
  }

  function rejectRewrite() {
    const next = textAfterReject(notes);
    setNotes(next.notes);
    setComparison(null);
    setSavedOnServer(false);
    setFeedback('Rewrite discarded. The note field is unchanged and nothing was saved.');
  }

  async function reportRewrite() {
    if (!comparison?.activityId) {
      setFeedback('There is no AI activity id, so this rewrite cannot be reported.');
      return;
    }
    setReporting(true);
    try {
      await reportIncorrectRewrite(comparison.activityId);
      setSavedOnServer(false);
      setFeedback('Feedback sent. The note was not saved.');
    } catch (error) {
      setFeedback(hmoreErrorMessage(error, 'Could not send feedback. The note was not saved.'));
    } finally {
      setReporting(false);
    }
  }

  function clearNote() {
    speech.cancel();
    setNotes('');
    editedRef.current = false;
    setComparison(null);
    setEditedRewritten('');
    setSavedOnServer(false);
    setFeedback('');
  }

  async function retryDictation() {
    speech.cancel();
    await speech.start();
  }

  return (
    <StaffPage
      title="Notes"
      subtitle="Daily logs for your caseload. Dictation uses this device. AI rewrite is optional and does not save the note."
      onRefresh={() => { logs.refetch(); caseload.refetch(); }}
      refreshing={logs.isRefetching}
    >
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
      <Input label="Note" value={notes} onChangeText={onNotesChange} multiline />
      {speech.listening ? <Text accessibilityLiveRegion="polite">Listening…</Text> : null}
      {speech.interim ? <Feedback text={`Hearing: ${speech.interim}`} /> : null}
      {speech.message ? <Feedback text={speech.message} /> : null}
      <Button
        title={speech.listening ? 'Stop dictation' : 'Start dictation'}
        variant="outline"
        onPress={speech.listening ? speech.stop : speech.start}
        fullWidth
      />
      {speech.listening ? <Button title="Cancel dictation" variant="ghost" onPress={speech.cancel} fullWidth /> : null}
      <Button title="Retry" variant="outline" onPress={() => void retryDictation()} fullWidth />
      <Button title="Clear" variant="ghost" onPress={clearNote} fullWidth />
      <Button title="Save draft" variant="outline" onPress={() => void saveDraft()} loading={busy} disabled={busy || tenants.length === 0} fullWidth />
      <Button title="Save original note" onPress={requestSave} loading={busy} disabled={busy || tenants.length === 0} fullWidth />
      <Button title="AI Professional Rewrite" variant="outline" onPress={() => void rewrite()} loading={busy} disabled={busy || tenants.length === 0} fullWidth />
      {feedback ? <Feedback text={feedback} tone={savedOnServer ? 'ok' : 'warn'} /> : null}
      {comparison ? (
        <RewriteComparison
          original={comparison.original}
          rewritten={editedRewritten}
          onChangeRewritten={setEditedRewritten}
          onAccept={acceptRewrite}
          onReject={rejectRewrite}
          onReport={() => void reportRewrite()}
          canReport={!!comparison.activityId}
          reporting={reporting}
        />
      ) : null}
      {(logs.data?.items ?? []).map((log) => (
        <RecordCard key={log.id} title={log.summary} status={log.status} detail={`${log.log_date} · ${staffLabel(log.activity_category)}`} />
      ))}
      {logs.isError ? <Feedback text={hmoreErrorMessage(logs.error, 'Could not list notes.')} /> : null}
    </StaffPage>
  );
}
