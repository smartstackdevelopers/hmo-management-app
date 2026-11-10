import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { hasPermission } from '@/lib/hmore/roles';
import { decideApproval, listApprovalInbox } from '@/lib/hmore/services/staff/approvals';

export function ApprovalInbox() {
  const { hmore } = useAuth();
  const client = useQueryClient();
  const canDecide = hasPermission(hmore?.rbac.permissions, 'approvals.decide');
  const query = useQuery({ queryKey: ['hmore', 'staff', 'approvals'], queryFn: listApprovalInbox });
  const [reason, setReason] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);

  if (query.isLoading) return <LoadingScreen message="Loading approvals..." />;
  if (query.isError) {
    return <ErrorState message={hmoreErrorMessage(query.error, 'Approvals are not available for this account')} onRetry={query.refetch} />;
  }

  const items = query.data?.items ?? [];

  async function decide(action: 'approve' | 'reject' | 'request_information') {
    const item = items.find((row) => row.source_id === selected);
    if (!item || !canDecide) return;
    setBusy(true);
    setFeedback('');
    try {
      await decideApproval(item.source_type, item.source_id, { action, reason: reason.trim() || null });
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'approvals'] });
      setFeedback('Decision sent. The status below is the latest inbox from the server.');
      setReason('');
    } catch (error) {
      setFeedback(hmoreErrorMessage(error, 'The decision was not saved.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <StaffPage
      title="Approvals"
      subtitle={canDecide ? 'You can record a decision. The status is whatever the server returns after refresh.' : 'You can read the inbox. This account cannot decide approvals.'}
      onRefresh={query.refetch}
      refreshing={query.isRefetching}
    >
      {items.length === 0 ? <RecordCard title="Inbox empty" detail="No approval items were returned." /> : null}
      {items.map((item) => (
        <RecordCard
          key={`${item.source_type}:${item.source_id}`}
          title={item.title}
          status={item.status}
          detail={`${item.reference} · ${item.source_type}`}
          onPress={() => setSelected(item.source_id)}
        />
      ))}
      {canDecide && selected ? (
        <>
          <Input label="Reason" value={reason} onChangeText={setReason} />
          <Button title="Approve" onPress={() => decide('approve')} loading={busy} fullWidth />
          <Button title="Request information" variant="outline" onPress={() => decide('request_information')} fullWidth />
          <Button title="Reject" variant="outline" onPress={() => decide('reject')} fullWidth />
        </>
      ) : null}
      {feedback ? <Feedback text={feedback} tone={feedback.startsWith('Decision sent') ? 'ok' : 'warn'} /> : null}
    </StaffPage>
  );
}
