import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { FilterChips, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { RepairCard } from '@/components/maintenance/RepairCard';
import { StaffMobileLater } from '@/components/tenant/StaffMobileLater';
import { TenantMaintenanceList } from '@/components/tenant/TenantMaintenanceList';
import { Button } from '@/components/ui/Button';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useMaintenance } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import {
  RepairFilter,
  isOpenStatus,
  matchesRepairFilter,
} from '@/lib/maintenance';

const FILTERS: { id: RepairFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'open', label: 'Open' },
  { id: 'urgent', label: 'Urgent' },
  { id: 'done', label: 'Done' },
];

function LegacyMaintenanceScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(TAB_ROLES.maintenance);
  if (guard) return guard;

  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useMaintenance();
  const [filter, setFilter] = useState<RepairFilter>('all');
  const [query, setQuery] = useState('');
  const canReport = ['tenant', 'landlord', 'property_manager'].includes(user?.role ?? '');
  const isTenant = user?.role === 'tenant';

  const requests = data?.requests ?? [];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return requests.filter((row) => {
      if (!matchesRepairFilter(row, filter)) return false;
      if (!needle) return true;
      const haystack = `${row.title} ${row.property?.name ?? ''} ${row.room?.name ?? ''} ${row.category}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [requests, filter, query]);

  const openCount = requests.filter((row) => isOpenStatus(row.status)).length;

  if (isLoading) return <LoadingScreen message="Loading repairs..." />;
  if (error) return <ErrorState message="Could not load repairs" onRetry={refetch} />;

  return (
    <ListScreen
      data={filtered}
      keyExtractor={(item) => item.id}
      refreshing={isRefetching}
      onRefresh={refetch}
      contentContainerStyle={filtered.length === 0 ? styles.emptyList : undefined}
      ListHeaderComponent={
        <View style={styles.header}>
          <ScreenHeader
            title="Repairs"
            subtitle={openCount > 0 ? `${openCount} open` : 'Track repairs across your properties.'}
            action={
              canReport ? (
                <Button
                  title={isTenant ? 'Report' : 'New'}
                  icon="add"
                  size="sm"
                  onPress={() => router.push('/(app)/maintenance/new')}
                />
              ) : undefined
            }
          />
          <SearchField value={query} onChangeText={setQuery} placeholder="Search repairs" />
          <FilterChips options={FILTERS} value={filter} onChange={(id) => setFilter(id as RepairFilter)} />
          {filtered.length > 0 ? (
            <Text style={styles.resultCount}>
              {filtered.length} repair{filtered.length === 1 ? '' : 's'}
            </Text>
          ) : null}
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title={emptyTitle(filter, isTenant)}
          message={emptyMessage(filter, isTenant)}
          icon={filter === 'urgent' ? 'alert-circle-outline' : 'construct-outline'}
          actionLabel={canReport && filter !== 'done' ? 'Report a repair' : undefined}
          onAction={canReport && filter !== 'done' ? () => router.push('/(app)/maintenance/new') : undefined}
        />
      }
      renderItem={({ item }) => <RepairCard item={item} />}
    />
  );
}

function emptyTitle(filter: RepairFilter, isTenant: boolean): string {
  if (filter === 'urgent') return 'No urgent repairs';
  if (filter === 'open') return isTenant ? 'Nothing open' : 'No open repairs';
  if (filter === 'done') return 'No completed repairs yet';
  return 'No repair requests';
}

function emptyMessage(filter: RepairFilter, isTenant: boolean): string {
  if (filter === 'urgent') return 'High and emergency jobs will show here.';
  if (filter === 'open') {
    return isTenant
      ? 'All clear — report a leak, heating issue, or other problem here.'
      : 'Your portfolio has no open maintenance jobs.';
  }
  if (filter === 'done') return 'Finished jobs will appear in this list.';
  return 'Report a repair to get started.';
}

const styles = StyleSheet.create({
  emptyList: { flexGrow: 1 },
  header: { marginBottom: theme.spacing.sm },
  resultCount: {
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textMuted,
    marginTop: -4,
    marginBottom: theme.spacing.sm,
  },
});

export default function MaintenanceScreen() {
  const { hmore, user } = useAuth();
  if (hmore && user?.role === 'tenant') return <TenantMaintenanceList />;
  if (hmore) return <StaffMobileLater />;
  return <LegacyMaintenanceScreen />;
}
