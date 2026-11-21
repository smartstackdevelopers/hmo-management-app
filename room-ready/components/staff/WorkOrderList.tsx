import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Text } from 'react-native';

import { FilterChips, SearchField, titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { repairStatusText, repairStatusTone } from '@/components/maintenance/repairTone';
import { DraftBadge, StaffPage, StatusRow } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listAssignedWorkOrders } from '@/lib/hmore/services/staff/workOrders';
import type { MaintenanceRequest } from '@/lib/hmore/types';

type Filter = 'all' | 'assigned' | 'progress' | 'done';

const DONE = new Set(['completed', 'closed', 'cancelled', 'done']);
const PROGRESS = new Set(['in_progress', 'on_hold']);

function bucket(status: string): Exclude<Filter, 'all'> {
  const value = status.toLowerCase();
  if (DONE.has(value)) return 'done';
  if (PROGRESS.has(value)) return 'progress';
  return 'assigned';
}

function detailLine(order: MaintenanceRequest): string {
  const when = order.scheduled_visit_at ? formatUKDate(order.scheduled_visit_at) : null;
  return [order.reference_number, when].filter(Boolean).join(' · ');
}

export function WorkOrderList() {
  useHideTabHeader();
  const drafts = useStaffDrafts();
  const [queryText, setQueryText] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const query = useQuery({ queryKey: ['hmore', 'staff', 'work-orders'], queryFn: listAssignedWorkOrders });

  const orders = query.data?.items ?? [];
  const visible = useMemo(() => {
    const needle = queryText.trim().toLowerCase();
    return orders.filter((order) => {
      if (filter !== 'all' && bucket(order.status) !== filter) return false;
      if (!needle) return true;
      return `${order.title} ${order.reference_number}`.toLowerCase().includes(needle);
    });
  }, [orders, filter, queryText]);

  if (query.isLoading) return <LoadingScreen message="Loading work orders..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load work orders')} onRetry={query.refetch} />;

  return (
    <StaffPage title="Work orders" subtitle={`${orders.length} assigned`} onRefresh={query.refetch} refreshing={query.isRefetching}>
      <DraftBadge count={drafts.drafts.filter((draft) => draft.type === 'work_order_update').length} />
      <SearchField value={queryText} onChangeText={setQueryText} placeholder="Search jobs" />
      <FilterChips
        value={filter}
        onChange={(id) => setFilter(id as Filter)}
        options={[
          { id: 'all', label: 'All' },
          { id: 'assigned', label: 'Assigned' },
          { id: 'progress', label: 'In progress' },
          { id: 'done', label: 'Done' },
        ]}
      />
      {visible.length === 0 ? (
        <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 20 }}>
          {orders.length === 0 ? 'Nothing assigned was returned.' : 'No jobs match this search.'}
        </Text>
      ) : (
        visible.map((order) => (
          <StatusRow
            key={order.id}
            name={order.title}
            title={order.title}
            subtitle={detailLine(order)}
            chip={order.priority === 'urgent' || order.priority === 'emergency' || order.priority === 'high' ? titleCase(order.priority) : repairStatusText(order.status)}
            tone={order.priority === 'urgent' || order.priority === 'emergency' || order.priority === 'high' ? 'red' : repairStatusTone(order.status)}
            onPress={() => router.push(`/(app)/staff/work-order/${order.id}`)}
          />
        ))
      )}
    </StaffPage>
  );
}
