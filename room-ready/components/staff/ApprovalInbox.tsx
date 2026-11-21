import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigation } from 'expo-router';
import { useLayoutEffect, useMemo, useState } from 'react';

import { FilterChips, SearchField, titleCase } from '@/components/dashboard/mobileChrome';
import { BackLink, Feedback, StaffPage, StatusRow, statusTone } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { hasPermission } from '@/lib/hmore/roles';
import { decideApproval, listApprovalInbox } from '@/lib/hmore/services/staff/approvals';

export function ApprovalInbox() {
  const navigation = useNavigation();
  const { hmore } = useAuth();
  const client = useQueryClient();
  useLayoutEffect(() => {
    navigation.setOptions({ headerShown: false });
  }, [navigation]);
  const canDecide = hasPermission(hmore?.rbac.permissions, 'approvals.decide');
  const query = useQuery({ queryKey: ['hmore', 'staff', 'approvals'], queryFn: listApprovalInbox });
  const [reason, setReason] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const [queryText, setQueryText] = useState('');
  const [filter, setFilter] = useState('all');
  const items = query.data?.items ?? [];
  const sources = useMemo(() => [...new Set(items.map((item) => item.source_type).filter(Boolean))], [items]);
  const visible = useMemo(() => {
    const needle = queryText.trim().toLowerCase();
    return items.filter((item) => {
      if (filter !== 'all' && item.source_type !== filter) return false;
      if (!needle) return true;
      return `${item.title} ${item.reference} ${item.source_type}`.toLowerCase().includes(needle);
    });
  }, [items, filter, queryText]);

  if (query.isLoading) return <LoadingScreen message="Loading approvals..." />;
  if (query.isError) {
    return <ErrorState message={hmoreErrorMessage(query.error, 'Approvals are not available for this account')} onRetry={query.refetch} />;
  }

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
      subtitle={canDecide ? 'Approve or reject from the server inbox.' : 'You can read the inbox. This account cannot decide approvals.'}
      leading={<BackLink />}
      onRefresh={query.refetch}
      refreshing={query.isRefetching}
    >
      <SearchField value={queryText} onChangeText={setQueryText} placeholder="Search approvals" />
      <FilterChips
        value={filter}
        onChange={setFilter}
        options={[{ id: 'all', label: 'All' }, ...sources.map((source) => ({ id: source, label: titleCase(source) }))]}
      />
      {visible.length === 0 ? <Feedback text={items.length === 0 ? 'No approval items were returned.' : 'No approvals match this search.'} /> : null}
      {visible.map((item) => (
        <StatusRow
          key={`${item.source_type}:${item.source_id}`}
          name={item.title}
          title={item.title}
          subtitle={`${item.reference} · ${titleCase(item.source_type)}`}
          chip={titleCase(item.status)}
          tone={statusTone(item.status)}
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
