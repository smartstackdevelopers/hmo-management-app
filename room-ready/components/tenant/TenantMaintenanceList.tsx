import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { RefreshControl, StyleSheet, Text, View } from 'react-native';

import { SearchField, titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { TenantFilterChips } from '@/components/tenant/TenantFilterChips';
import { repairStatusText, repairStatusTone } from '@/components/maintenance/repairTone';
import { ActivityRow } from '@/components/tenant/ActivityRow';
import { useConnectivity } from '@/components/tenant/safeFetch';
import { TenantLoadError, TenantOffline } from '@/components/tenant/TenantStates';
import { shortDate, shortTime } from '@/components/tenant/tenantFormat';
import { Button } from '@/components/ui/Button';
import { Screen } from '@/components/ui/Screen';
import { EmptyState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { listMaintenance } from '@/lib/hmore/services/maintenance';
import type { MaintenanceRequest } from '@/lib/hmore/types';

const CLOSED = new Set(['completed', 'closed', 'cancelled']);
type Filter = 'all' | 'open' | 'scheduled' | 'done';

function matches(row: MaintenanceRequest, filter: Filter): boolean {
  const done = CLOSED.has(row.status);
  if (filter === 'done') return done;
  if (filter === 'open') return !done;
  if (filter === 'scheduled') return !done && !!row.scheduled_visit_at;
  return true;
}

function rowMeta(row: MaintenanceRequest): string {
  const where = titleCase(row.category_code || '');
  if (row.scheduled_visit_at) {
    return [where, shortDate(row.scheduled_visit_at), shortTime(row.scheduled_visit_at)].filter(Boolean).join(' · ');
  }
  return [where, shortDate(row.reported_at || row.created_at)].filter(Boolean).join(' · ');
}

export function TenantMaintenanceList() {
  useHideTabHeader();
  const { t, fontScale, prefs } = useI18n();
  const net = useConnectivity();
  const [filter, setFilter] = useState<Filter>('all');
  const [query, setQuery] = useState('');
  const repairsQuery = useQuery({
    queryKey: ['hmore', 'maintenance'],
    queryFn: () => listMaintenance({ page: 1, page_size: 50 }),
  });

  const rows = repairsQuery.data?.items ?? [];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter((row) => {
      if (!matches(row, filter)) return false;
      if (!needle) return true;
      return `${row.title} ${row.reference_number} ${row.category_code} ${row.description}`.toLowerCase().includes(needle);
    });
  }, [rows, filter, query]);

  const offline = net.data === 'offline';
  if (repairsQuery.isLoading && !repairsQuery.data) {
    if (offline) return <TenantOffline />;
    return <LoadingScreen message={t('repairs.loading')} />;
  }
  if (repairsQuery.error && !repairsQuery.data) {
    if (offline) return <TenantOffline />;
    return <TenantLoadError title={t('repairs.couldNot')} onRetry={() => repairsQuery.refetch()} />;
  }
  if (rows.length === 0) {
    return (
      <EmptyState
        title={t('repairs.emptyTitle')}
        message={t('repairs.emptyBody')}
        icon="card-outline"
        actionLabel={t('repairs.report')}
        onAction={() => router.push('/(app)/maintenance/new')}
      />
    );
  }

  const filters: { id: Filter; label: string }[] = [
    { id: 'all', label: t('repairs.all') },
    { id: 'open', label: t('repairs.open') },
    { id: 'scheduled', label: t('repairs.scheduled') },
    { id: 'done', label: t('repairs.done') },
  ];
  const contrast = prefs.highContrast;

  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={
        <RefreshControl
          refreshing={repairsQuery.isRefetching}
          onRefresh={() => {
            repairsQuery.refetch();
            net.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <View style={styles.header}>
        <View style={styles.headerCopy}>
          <Text style={[styles.title, { fontSize: 28 * fontScale }]} accessibilityRole="header">
            {t('nav.repairs')}
          </Text>
          <Text style={[styles.subtitle, { fontSize: 14 * fontScale }]}>{t('repairs.track')}</Text>
        </View>
        <Button
          title={t('repairs.reportShort')}
          accessibilityLabel={t('repairs.report')}
          icon="add"
          size="sm"
          onPress={() => router.push('/(app)/maintenance/new')}
        />
      </View>
      <SearchField value={query} onChangeText={setQuery} placeholder={t('repairs.search')} />
      <TenantFilterChips options={filters} value={filter} onChange={setFilter} />
      {filtered.length === 0 ? (
        <EmptyState compact title={t('repairs.emptyTitle')} message={t('repairs.emptyBody')} icon="construct-outline" />
      ) : (
        filtered.map((row) => (
          <ActivityRow
            key={row.id}
            highContrast={contrast}
            name={row.title}
            title={row.title}
            meta={rowMeta(row)}
            chip={repairStatusText(row.status)}
            chipTone={repairStatusTone(row.status)}
            onPress={() => router.push(`/(app)/maintenance/${row.id}`)}
          />
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: theme.spacing.md,
  },
  headerCopy: { flex: 1, minWidth: 0 },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.5 },
  subtitle: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 },
});
