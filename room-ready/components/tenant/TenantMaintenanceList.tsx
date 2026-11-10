import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { RefreshControl, Pressable, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listMaintenance } from '@/lib/hmore/services/maintenance';
import type { MaintenanceRequest } from '@/lib/hmore/types';

const CLOSED = new Set(['completed', 'closed', 'cancelled']);
type Filter = 'open' | 'urgent' | 'done' | 'all';

function matches(row: MaintenanceRequest, filter: Filter): boolean {
  const done = CLOSED.has(row.status);
  if (filter === 'done') return done;
  if (filter === 'open') return !done;
  if (filter === 'urgent') return !done && (row.priority === 'urgent' || row.priority === 'emergency' || row.priority === 'high');
  return true;
}

export function TenantMaintenanceList() {
  const { t } = useI18n();
  const [filter, setFilter] = useState<Filter>('open');
  const query = useQuery({
    queryKey: ['hmore', 'maintenance'],
    queryFn: () => listMaintenance({ page: 1, page_size: 50 }),
  });

  const rows = query.data?.items ?? [];
  const filtered = useMemo(() => rows.filter((row) => matches(row, filter)), [rows, filter]);

  if (query.isLoading) return <LoadingScreen message={t('repairs.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error, t('repairs.error'))} onRetry={query.refetch} />;

  return (
    <Screen
      refreshControl={
        <RefreshControl refreshing={query.isRefetching} onRefresh={query.refetch} tintColor={theme.colors.secondary} />
      }
    >
      <Button title={t('repairs.report')} accessibilityLabel={t('repairs.report')} onPress={() => router.push('/(app)/maintenance/new')} fullWidth />
      <View style={styles.filters}>
        {(['open', 'urgent', 'done', 'all'] as Filter[]).map((id) => {
          const active = filter === id;
          const label = id === 'open' ? t('repairs.open') : id === 'urgent' ? t('repairs.urgent') : id === 'done' ? t('repairs.done') : t('repairs.all');
          return (
            <Pressable
              key={id}
              accessibilityRole="button"
              accessibilityLabel={label}
              accessibilityState={{ selected: active }}
              onPress={() => setFilter(id)}
              style={[styles.chip, active && styles.chipActive]}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
            </Pressable>
          );
        })}
      </View>
      {filtered.length === 0 ? (
        <EmptyState title={t('repairs.emptyTitle')} message={t('repairs.emptyBody')} icon="construct-outline" />
      ) : (
        filtered.map((row) => (
          <Card key={row.id} style={styles.card} onPress={() => router.push(`/(app)/maintenance/${row.id}`)}>
            <View style={styles.header}>
              <Text style={styles.title}>{row.title}</Text>
              <Badge label={row.status.replace(/_/g, ' ')} format={false} />
            </View>
            <Text style={styles.meta}>
              {row.reference_number} · {row.priority} · {formatUKDate(row.reported_at || row.created_at)}
            </Text>
            {row.scheduled_visit_at ? (
              <Text style={styles.meta}>Visit {formatUKDate(row.scheduled_visit_at)}</Text>
            ) : null}
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: theme.spacing.md },
  chip: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.full,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: theme.colors.surface,
  },
  chipActive: { backgroundColor: theme.colors.secondary, borderColor: theme.colors.secondary },
  chipText: { fontFamily: FONT_SEMIBOLD, fontSize: 13, color: theme.colors.text },
  chipTextActive: { color: theme.colors.textInverse },
  card: { marginBottom: theme.spacing.sm },
  header: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, alignItems: 'center' },
  title: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text, flex: 1 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary, marginTop: 6, textTransform: 'capitalize' },
});
