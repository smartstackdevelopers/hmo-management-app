import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';

import { RecordCard, StaffPage } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getCaseDetail } from '@/lib/hmore/services/staff/caseload';

export function CaseDetail() {
  const { tenantId } = useLocalSearchParams<{ tenantId: string }>();
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ['hmore', 'staff', 'case', tenantId, user?.role],
    queryFn: () => getCaseDetail(user?.role, tenantId),
    enabled: !!tenantId,
  });

  if (query.isLoading) return <LoadingScreen message="Loading tenant..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load this tenant')} onRetry={query.refetch} />;

  const detail = query.data;
  const tenant = detail?.tenant;
  return (
    <StaffPage title={tenant?.preferred_name || tenant?.full_name || 'Tenant'} subtitle={tenant?.tenancy_reference || tenant?.status || ''} onRefresh={query.refetch} refreshing={query.isRefetching}>
      <RecordCard title="Status" status={tenant?.status} detail="Contact notes and needs are not shown on this screen." />
      {(detail?.recent_logs ?? []).map((log) => (
        <RecordCard key={log.id} title={log.summary} status={log.status} detail={log.log_date} />
      ))}
      {(detail?.recent_logs ?? []).length === 0 ? <RecordCard title="No recent notes" detail="The server did not return recent logs." /> : null}
      {(detail?.recent_handovers ?? []).map((handover) => (
        <RecordCard key={handover.id} title={handover.summary} status={handover.status} />
      ))}
    </StaffPage>
  );
}
