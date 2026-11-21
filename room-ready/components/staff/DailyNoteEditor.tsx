import { useQuery } from '@tanstack/react-query';
import { useCallback, useRef, useState } from 'react';
import { Alert, Switch, Text, View } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { RewriteComparison } from '@/components/staff/voice/RewriteComparison';
import { ChoiceRow, DraftBadge, Feedback, StaffPage, StatusRow, staffLabel, statusTone } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
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
import { ACTIVITY_CATEGORIES, INTERACTION_TYPES, listDailyLogs, type DailyLogInput } from '@/lib/hmore/services/staff/dailyLogs';

export function DailyNoteEditor() {
  useHideTabHeader();
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
  const [interaction, setInteraction] = useState<string>(INTERACTION_TYPES[0]);
  const [followUp, setFollowUp] = useState(false);
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
      interaction_type: interaction,
      summary: summary.trim(),
      notes: notes.trim(),
      follow_up_required: followUp,
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
      const draft = await drafts.save({ type: 'daily_log', payload: payload as unknown as Record<string, unknown> });
      const online = await isDeviceOnline({ ping: pingHmoreHealth });
      if (!online) {
        setFeedback('Saved on this device. It is not on the server yet.');
        return;
      }
      const report = await drafts.sync();
      const result = report.results.find((item) => item.id === draft.id);
      if (!result?.saved) {
        setFeedback(`${result?.error || 'Could not save the note.'} The note is still a draft on this device.`);
        return;
      }
      setSavedOnServer(true);
      setFeedback('Saved on the server.');
      setSummary('');
      setNotes('');
      editedRef.current = false;
      setComparison(null);
      await logs.refetch();
    } catch (error) {
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
      title="New daily log"
      subtitle="Saved only after you confirm. Dictation stays on this device."
      onRefresh={() => { logs.refetch(); caseload.refetch(); }}
      refreshing={logs.isRefetching}
    >
      <DraftBadge count={drafts.drafts.filter((draft) => draft.type === 'daily_log').length} />
      {drafts.drafts.filter((draft) => draft.type === 'daily_log' && draft.payload.tenant_id === selectedTenant && draft.lastError).map((draft) => (
        <Feedback key={draft.id} text={draft.lastError || ''} tone="warn" />
      ))}
      {tenants.length === 0 ? <Feedback text="A note needs someone on your caseload." tone="warn" /> : (
        <>
          <Text style={fieldLabel}>Tenant</Text>
          <ChoiceRow
            value={selectedTenant}
            onChange={setTenantId}
            options={tenants.map((item) => ({ id: item.tenant_id, label: item.tenant_preferred_name || item.tenant_full_name || 'Tenant' }))}
          />
        </>
      )}
      <Text style={fieldLabel}>Contact type</Text>
      <ChoiceRow
        value={interaction}
        onChange={setInteraction}
        options={INTERACTION_TYPES.map((item) => ({ id: item, label: staffLabel(item) }))}
      />
      <Text style={fieldLabel}>Category</Text>
      <ChoiceRow
        value={category}
        onChange={setCategory}
        options={ACTIVITY_CATEGORIES.map((item) => ({ id: item, label: staffLabel(item) }))}
      />
      <Input label="Summary" value={summary} onChangeText={setSummary} multiline />
      <Input label="Note" value={notes} onChangeText={onNotesChange} multiline />
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, minHeight: 44 }}>
        <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.text }}>Follow-up needed</Text>
        <Switch
          accessibilityLabel="Follow-up needed"
          value={followUp}
          onValueChange={setFollowUp}
        />
      </View>
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
      <Button title="Save log" onPress={requestSave} loading={busy} disabled={busy || tenants.length === 0} fullWidth />
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
        <StatusRow
          key={log.id}
          name={log.summary}
          title={log.summary}
          subtitle={[log.log_date, staffLabel(log.activity_category)].filter(Boolean).join(' · ')}
          chip={staffLabel(log.status)}
          tone={statusTone(log.status)}
        />
      ))}
      {logs.isError ? <Feedback text={hmoreErrorMessage(logs.error, 'Could not list notes.')} /> : null}
    </StaffPage>
  );
}

const fieldLabel = { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: 8, marginTop: 4 };
