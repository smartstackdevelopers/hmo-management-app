import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';

import { ChoiceRow, DraftBadge, Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { isDeviceOnline, pingHmoreHealth } from '@/lib/hmore/staff/network';
import { listVisits } from '@/lib/hmore/services/staff/visits';

const STATUSES = ['scheduled', 'confirmed', 'in_progress', 'completed', 'missed', 'cancelled'];

export function VisitBoard() {
  const params = useLocalSearchParams<{ visitId?: string }>();
  const drafts = useStaffDrafts();
  const query = useQuery({ queryKey: ['hmore', 'staff', 'visits'], queryFn: () => listVisits() });
  const [selected, setSelected] = useState(params.visitId || '');
  const [status, setStatus] = useState('completed');
  const [outcome, setOutcome] = useState('');
  const [feedback, setFeedback] = useState('');
  const [savedOnServer, setSavedOnServer] = useState(false);
  const [busy, setBusy] = useState(false);

  if (query.isLoading) return <LoadingScreen message="Loading visits..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load visits')} onRetry={query.refetch} />;

  const visits = query.data?.items ?? [];
  const current = visits.find((visit) => visit.id === (selected || visits[0]?.id)) ?? visits[0];

  async function save() {
    if (!current) return;
    const payload = {
      visit_id: current.id,
      status,
      outcome: outcome.trim(),
      notes: current.notes,
      if_match_updated_at: current.updated_at,
    };
    setBusy(true);
    setSavedOnServer(false);
    try {
      const draft = await drafts.save({
        type: 'visit_update',
        payload,
        serverUpdatedAt: current.updated_at,
      });
      const online = await isDeviceOnline({ ping: pingHmoreHealth });
      if (!online) {
        setFeedback('Saved on this device. The visit status is still the server status until sync.');
        return;
      }
      const report = await drafts.sync();
      const result = report.results.find((item) => item.id === draft.id);
      if (!result?.saved) {
        setFeedback(result?.error || 'The update is still a draft.');
        return;
      }
      setSavedOnServer(true);
      const refreshed = await query.refetch();
      const confirmed = refreshed.data?.items.find((visit) => visit.id === current.id);
      setFeedback(`Server status: ${confirmed?.status ?? status}`);
    } catch (error) {
      setFeedback(`${hmoreErrorMessage(error)} The update is still a draft.`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <StaffPage title="Visits" subtitle="Status shown here is the status returned by the server." onRefresh={query.refetch} refreshing={query.isRefetching}>
      <DraftBadge count={drafts.drafts.filter((draft) => draft.type === 'visit_update').length} />
      {current ? drafts.drafts.filter((draft) => draft.payload.visit_id === current.id && draft.lastError).map((draft) => (
        <Feedback key={draft.id} text={draft.lastError || ''} tone="warn" />
      )) : null}
      {visits.length === 0 ? <RecordCard title="No visits" detail="No assigned visits were returned." /> : null}
      {visits.map((visit) => (
        <RecordCard
          key={visit.id}
          title={visit.purpose}
          status={visit.status}
          detail={`${formatUKDate(visit.scheduled_at)}${visit.location ? ` · ${visit.location}` : ''}`}
          onPress={() => setSelected(visit.id)}
        />
      ))}
      {current ? (
        <>
          <ChoiceRow value={status} onChange={setStatus} options={STATUSES.map((item) => ({ id: item, label: item.replace(/_/g, ' ') }))} />
          <Input label="Outcome" value={outcome} onChangeText={setOutcome} />
          <Button title="Update visit" onPress={save} loading={busy} fullWidth />
          {feedback ? <Feedback text={feedback} tone={savedOnServer ? 'ok' : 'warn'} /> : null}
        </>
      ) : null}
    </StaffPage>
  );
}
