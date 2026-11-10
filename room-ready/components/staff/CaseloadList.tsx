import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';

import { RecordCard, StaffPage, staffLabel } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listCaseload } from '@/lib/hmore/services/staff/caseload';

export function CaseloadList() {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ['hmore', 'staff', 'caseload', user?.role],
    queryFn: () => listCaseload(user?.role, { page: 1, page_size: 50, status: 'active' }),
  });

  if (query.isLoading) return <LoadingScreen message="Loading your tenants..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load caseload')} onRetry={query.refetch} />;

  const items = query.data?.items ?? [];
  return (
    <StaffPage title="My tenants" subtitle="People on your caseload. Nothing is added here that the server did not return." onRefresh={query.refetch} refreshing={query.isRefetching}>
      {items.length === 0 ? <RecordCard title="No assigned tenants" detail="When a case is assigned to you, it will show up here." /> : null}
      {items.map((item) => (
        <RecordCard
          key={item.id}
          title={item.tenant_preferred_name || item.tenant_full_name || 'Tenant'}
          status={item.status}
          detail={staffLabel(item.assignment_notes || '') || undefined}
          onPress={() => router.push(`/(app)/staff/case/${item.tenant_id}`)}
        />
      ))}
    </StaffPage>
  );
}
