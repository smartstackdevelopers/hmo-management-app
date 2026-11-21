import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Text } from 'react-native';

import { FilterChips, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { StaffPage, StatusRow, staffLabel, statusTone } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listCaseload, type CaseAssignment } from '@/lib/hmore/services/staff/caseload';

function tenantName(item: CaseAssignment): string {
  return item.tenant_preferred_name || item.tenant_full_name || 'Tenant';
}

export function CaseloadList() {
  useHideTabHeader();
  const { user } = useAuth();
  const [queryText, setQueryText] = useState('');
  const [filter, setFilter] = useState('all');
  const query = useQuery({
    queryKey: ['hmore', 'staff', 'caseload', user?.role],
    queryFn: () => listCaseload(user?.role, { page: 1, page_size: 50, status: 'active' }),
  });

  const items = query.data?.items ?? [];
  const statuses = useMemo(
    () => [...new Set(items.map((item) => item.status).filter(Boolean))],
    [items],
  );
  const chips = useMemo(() => {
    const options = [{ id: 'all', label: 'All' }, ...statuses.map((status) => ({ id: `status:${status}`, label: staffLabel(status) }))];
    if (items.some((item) => (item.pending_handover_count ?? 0) > 0)) {
      options.push({ id: 'handover', label: 'Handover' });
    }
    return options;
  }, [items, statuses]);

  const visible = useMemo(() => {
    const needle = queryText.trim().toLowerCase();
    return items.filter((item) => {
      if (filter === 'handover' && !(item.pending_handover_count ?? 0)) return false;
      if (filter.startsWith('status:') && item.status !== filter.slice(7)) return false;
      if (!needle) return true;
      return `${tenantName(item)} ${item.assignment_notes ?? ''}`.toLowerCase().includes(needle);
    });
  }, [items, filter, queryText]);

  if (query.isLoading) return <LoadingScreen message="Loading your tenants..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load caseload')} onRetry={query.refetch} />;

  const total = query.data?.total ?? items.length;

  return (
    <StaffPage
      title="My tenants"
      subtitle={total === 1 ? '1 assigned' : `${total} assigned`}
      onRefresh={query.refetch}
      refreshing={query.isRefetching}
    >
      <SearchField value={queryText} onChangeText={setQueryText} placeholder="Search tenants" />
      <FilterChips options={chips} value={filter} onChange={setFilter} />
      {visible.length === 0 ? (
        <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 20 }}>
          {items.length === 0 ? 'When a case is assigned to you, it will show up here.' : 'No tenants match this search.'}
        </Text>
      ) : (
        visible.map((item) => (
          <StatusRow
            key={item.id}
            name={tenantName(item)}
            title={tenantName(item)}
            subtitle={item.assignment_notes?.trim() || undefined}
            chip={item.status ? staffLabel(item.status) : undefined}
            tone={statusTone(item.status)}
            onPress={() => router.push(`/(app)/staff/case/${item.tenant_id}`)}
          />
        ))
      )}
    </StaffPage>
  );
}
