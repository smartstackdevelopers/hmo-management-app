import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { RepairCard } from '@/components/maintenance/RepairCard';
import { StaffMobileLater } from '@/components/tenant/StaffMobileLater';
import { TenantMaintenanceList } from '@/components/tenant/TenantMaintenanceList';
import { Button } from '@/components/ui/Button';
import { ListScreen } from '@/components/ui/ListScreen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useMaintenance } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import {
  RepairFilter,
  isOpenStatus,
  isUrgentPriority,
  matchesRepairFilter,
} from '@/lib/maintenance';

const FILTERS: { id: RepairFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'open', label: 'Open' },
  { id: 'urgent', label: 'Urgent' },
  { id: 'done', label: 'Done' },
];

function LegacyMaintenanceScreen() {
  const guard = useRoleGuard(TAB_ROLES.maintenance);
  if (guard) return guard;

  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useMaintenance();
  const [filter, setFilter] = useState<RepairFilter>('open');
  const canReport = ['tenant', 'landlord', 'property_manager'].includes(user?.role ?? '');
  const isTenant = user?.role === 'tenant';

  const requests = data?.requests ?? [];
  const filtered = useMemo(
    () => requests.filter((r) => matchesRepairFilter(r, filter)),
    [requests, filter]
  );

  const openCount = requests.filter((r) => isOpenStatus(r.status)).length;
  const urgentCount = requests.filter(
    (r) => isOpenStatus(r.status) && isUrgentPriority(r.priority)
  ).length;
  const doneCount = requests.length - openCount;

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
          <View style={styles.summary}>
            <SummaryStat label="Open" value={openCount} tone="warning" />
            <SummaryStat label="Urgent" value={urgentCount} tone="error" />
            <SummaryStat label="Done" value={doneCount} tone="success" />
          </View>

          {canReport && (
            <Button
              title={isTenant ? 'Report a repair' : 'New repair'}
              onPress={() => router.push('/(app)/maintenance/new')}
              fullWidth
              style={styles.cta}
            />
          )}

          <View style={styles.filters}>
            {FILTERS.map((f) => {
              const active = filter === f.id;
              return (
                <Pressable
                  key={f.id}
                  onPress={() => setFilter(f.id)}
                  style={[styles.chip, active && styles.chipActive]}
                >
                  <Text style={[styles.chipText, active && styles.chipTextActive]}>{f.label}</Text>
                </Pressable>
              );
            })}
          </View>

          {filtered.length > 0 && (
            <Text style={styles.resultCount}>
              {filtered.length} repair{filtered.length === 1 ? '' : 's'}
              {filter !== 'all' ? ` · ${FILTERS.find((f) => f.id === filter)?.label}` : ''}
            </Text>
          )}
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

function SummaryStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: 'warning' | 'error' | 'success';
}) {
  const colors = {
    warning: { bg: theme.colors.warningLight, text: theme.colors.warning },
    error: { bg: theme.colors.errorLight, text: theme.colors.error },
    success: { bg: theme.colors.successLight, text: theme.colors.success },
  }[tone];

  return (
    <View style={[styles.stat, { backgroundColor: colors.bg }]}>
      <Text style={[styles.statValue, { color: colors.text }]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
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
  summary: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.md },
  stat: {
    flex: 1,
    borderRadius: theme.radius.lg,
    paddingVertical: 12,
    paddingHorizontal: 8,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 22,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    letterSpacing: -0.4,
  },
  statLabel: {
    fontSize: 12,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  cta: { marginBottom: theme.spacing.md },
  filters: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: theme.spacing.sm,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: theme.radius.full,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
  },
  chipActive: {
    backgroundColor: theme.colors.secondary,
    borderColor: theme.colors.secondary,
  },
  chipText: {
    fontSize: 13,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  chipTextActive: { color: theme.colors.textInverse },
  resultCount: {
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textMuted,
    marginBottom: theme.spacing.sm,
  },
});

export default function MaintenanceScreen() {
  const { hmore, user } = useAuth();
  if (hmore && user?.role === 'tenant') return <TenantMaintenanceList />;
  if (hmore) return <StaffMobileLater />;
  return <LegacyMaintenanceScreen />;
}
