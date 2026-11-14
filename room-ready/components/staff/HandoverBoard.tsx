import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';

import { ChoiceRow, Feedback, RecordCard, StaffPage } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getCaseDetail, listCaseload } from '@/lib/hmore/services/staff/caseload';
import {
  createHandover,
  listHandovers,
  type HandoverPriority,
} from '@/lib/hmore/services/staff/handovers';

const PRIORITIES: HandoverPriority[] = ['low', 'normal', 'high', 'urgent'];

export function HandoverBoard() {
  const { tenantId: paramTenantId } = useLocalSearchParams<{ tenantId?: string }>();
  const { user } = useAuth();
  const client = useQueryClient();
  const listQuery = useQuery({
    queryKey: ['hmore', 'staff', 'handovers', paramTenantId],
    queryFn: () =>
      listHandovers(user?.role, {
        page: 1,
        page_size: 50,
        tenant_id: paramTenantId,
        pending_only: !paramTenantId,
      }),
  });
  const caseloadQuery = useQuery({
    queryKey: ['hmore', 'staff', 'caseload', 'handover-form', user?.role],
    queryFn: () => listCaseload(user?.role, { page: 1, page_size: 50, status: 'active' }),
  });

  const [tenantId, setTenantId] = useState(paramTenantId ?? '');
  const [recipientUserId, setRecipientUserId] = useState('');
  const [summary, setSummary] = useState('');
  const [caseUpdates, setCaseUpdates] = useState('');
  const [priority, setPriority] = useState<HandoverPriority>('normal');
  const [submitImmediately, setSubmitImmediately] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ['hmore', 'staff', 'case', tenantId, user?.role],
    queryFn: () => getCaseDetail(user?.role, tenantId),
    enabled: !!tenantId,
  });

  const recipientOptions = useMemo(() => {
    const selfId = user?.id ?? '';
    const fromAssignments = (detailQuery.data?.assignments ?? [])
      .map((row) => row.support_worker_user_id)
      .filter((id) => id && id !== selfId);
    return [...new Set(fromAssignments)];
  }, [detailQuery.data?.assignments, user?.id]);

  const createMutation = useMutation({
    mutationFn: () =>
      createHandover(user?.role, {
        tenant_id: tenantId,
        recipient_user_id: recipientUserId.trim(),
        summary: summary.trim(),
        case_updates: caseUpdates.trim() || null,
        priority,
        submit: submitImmediately,
      }),
    onSuccess: async () => {
      setSummary('');
      setCaseUpdates('');
      setFormError(null);
      await client.invalidateQueries({ queryKey: ['hmore', 'staff', 'handovers'] });
      await listQuery.refetch();
    },
    onError: (error) => setFormError(hmoreErrorMessage(error, 'Could not create handover')),
  });

  if (listQuery.isLoading) return <LoadingScreen message="Loading handovers..." />;
  if (listQuery.isError) {
    return <ErrorState message={hmoreErrorMessage(listQuery.error, 'Could not load handovers')} onRetry={listQuery.refetch} />;
  }

  const handovers = listQuery.data?.items ?? [];
  const tenants = caseloadQuery.data?.items ?? [];

  return (
    <StaffPage
      title="Handovers"
      subtitle="Create and view case handovers for assigned tenants."
      onRefresh={() => {
        listQuery.refetch();
        caseloadQuery.refetch();
      }}
      refreshing={listQuery.isRefetching}
    >
      {handovers.length === 0 ? (
        <RecordCard title="No handovers" detail={paramTenantId ? 'None for this tenant yet.' : 'No pending handovers returned.'} />
      ) : (
        handovers.map((handover) => (
          <RecordCard
            key={handover.id}
            title={handover.summary}
            status={handover.status}
            detail={`${handover.tenant_preferred_name ?? handover.tenant_id} · ${formatUKDate(handover.handover_at)} · ${handover.priority}`}
          />
        ))
      )}

      <RecordCard title="New handover" detail="Recipient must be another support worker on the caseload." />
      {tenants.length > 0 ? (
        <ChoiceRow
          value={tenantId}
          onChange={(value) => {
            setTenantId(value);
            setRecipientUserId('');
          }}
          options={tenants.map((item) => ({
            id: item.tenant_id,
            label: item.tenant_preferred_name || item.tenant_full_name || item.tenant_id,
          }))}
        />
      ) : (
        <Input label="Tenant ID" value={tenantId} onChangeText={setTenantId} autoCapitalize="none" />
      )}
      {recipientOptions.length > 0 ? (
        <ChoiceRow
          value={recipientUserId}
          onChange={setRecipientUserId}
          options={recipientOptions.map((id) => ({ id, label: `Colleague ${id.slice(0, 8)}…` }))}
        />
      ) : (
        <Input
          label="Recipient user ID"
          value={recipientUserId}
          onChangeText={setRecipientUserId}
          autoCapitalize="none"
          hint="UUID of the receiving support worker"
        />
      )}
      <Input label="Summary" value={summary} onChangeText={setSummary} />
      <Input label="Case updates" value={caseUpdates} onChangeText={setCaseUpdates} multiline numberOfLines={4} />
      <ChoiceRow
        value={priority}
        onChange={(value) => setPriority(value as HandoverPriority)}
        options={PRIORITIES.map((item) => ({ id: item, label: item }))}
      />
      <ChoiceRow
        value={submitImmediately ? 'yes' : 'no'}
        onChange={(value) => setSubmitImmediately(value === 'yes')}
        options={[
          { id: 'yes', label: 'Submit immediately' },
          { id: 'no', label: 'Save as draft' },
        ]}
      />
      <Button
        title="Create handover"
        onPress={() => {
          if (!tenantId.trim() || !recipientUserId.trim() || !summary.trim()) {
            setFormError('Tenant, recipient, and summary are required.');
            return;
          }
          createMutation.mutate();
        }}
        loading={createMutation.isPending}
        fullWidth
      />
      {formError ? <Feedback text={formError} tone="warn" /> : null}
      {paramTenantId ? (
        <Button title="Back to tenant" variant="outline" onPress={() => router.push(`/(app)/staff/case/${paramTenantId}`)} fullWidth />
      ) : null}
    </StaffPage>
  );
}