import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';

import { DraftBadge, RecordCard, StaffPage } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listAssignedWorkOrders } from '@/lib/hmore/services/staff/workOrders';

export function WorkOrderList() {
  const drafts = useStaffDrafts();
  const query = useQuery({ queryKey: ['hmore', 'staff', 'work-orders'], queryFn: listAssignedWorkOrders });

  if (query.isLoading) return <LoadingScreen message="Loading work orders..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load work orders')} onRetry={query.refetch} />;

  const orders = query.data?.items ?? [];
  return (
    <StaffPage title="Work orders" subtitle="Assigned maintenance. Open a job to see the server status." onRefresh={query.refetch} refreshing={query.isRefetching}>
      <DraftBadge count={drafts.drafts.filter((draft) => draft.type === 'work_order_update').length} />
      {orders.length === 0 ? <RecordCard title="No work orders" detail="Nothing assigned was returned." /> : null}
      {orders.map((order) => (
        <RecordCard
          key={order.id}
          title={order.title}
          status={`${order.status}${order.approval_status ? ` · ${order.approval_status}` : ''}`}
          detail={order.reference_number}
          onPress={() => router.push(`/(app)/staff/work-order/${order.id}`)}
        />
      ))}
    </StaffPage>
  );
}
