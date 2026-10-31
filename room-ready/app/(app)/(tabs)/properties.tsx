import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { PropertyCard } from '@/components/property/PropertyCard';
import { Button } from '@/components/ui/Button';
import { ListScreen } from '@/components/ui/ListScreen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useProperties } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { assessPropertyCompliance } from '@/lib/compliance';

type PropertyFilter = 'all' | 'attention' | 'voids';

const FILTERS: { id: PropertyFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'attention', label: 'Needs attention' },
  { id: 'voids', label: 'Has voids' },
];

export default function PropertiesScreen() {
  const guard = useRoleGuard(TAB_ROLES.properties);
  if (guard) return guard;

  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useProperties();
  const canAdd = ['landlord', 'admin'].includes(user?.role ?? '');
  const [filter, setFilter] = useState<PropertyFilter>('all');

  const properties = data?.properties ?? [];

  const filtered = useMemo(() => {
    return properties.filter((p) => {
      const occupied = p.rooms?.filter((r) => r.status === 'occupied').length ?? 0;
      const total = p.rooms?.length ?? 0;
      const voids = total - occupied;
      const score = assessPropertyCompliance(p).score;
      const repairs = p._count?.maintenance ?? 0;
      if (filter === 'voids') return voids > 0;
      if (filter === 'attention') return score < 85 || repairs > 0;
      return true;
    });
  }, [properties, filter]);

  const occupied = properties.reduce(
    (sum, p) => sum + (p.rooms?.filter((r) => r.status === 'occupied').length ?? 0),
    0
  );
  const rooms = properties.reduce((sum, p) => sum + (p.rooms?.length ?? 0), 0);
  const attention = properties.filter((p) => {
    const score = assessPropertyCompliance(p).score;
    return score < 85 || (p._count?.maintenance ?? 0) > 0;
  }).length;

  if (isLoading) return <LoadingScreen message="Loading properties..." />;
  if (error) return <ErrorState message="Could not load properties" onRetry={refetch} />;

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
            <SummaryStat label="HMOs" value={properties.length} />
            <SummaryStat label="Occupied" value={`${occupied}/${rooms || 0}`} />
            <SummaryStat label="Attention" value={attention} warn={attention > 0} />
          </View>

          {canAdd && (
            <Button
              title="Add property"
              onPress={() => router.push('/(app)/property/new')}
              fullWidth
              style={styles.cta}
            />
          )}

          {properties.length > 0 && (
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
          )}

          {filtered.length > 0 && (
            <Text style={styles.resultCount}>
              {filtered.length} propert{filtered.length === 1 ? 'y' : 'ies'}
            </Text>
          )}
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title={properties.length === 0 ? 'No properties yet' : 'Nothing in this filter'}
          message={
            properties.length === 0
              ? 'Add your first HMO to manage rooms, compliance and listings.'
              : 'Try another filter to see more of your portfolio.'
          }
          icon="business-outline"
          actionLabel={canAdd && properties.length === 0 ? 'Add property' : undefined}
          onAction={canAdd && properties.length === 0 ? () => router.push('/(app)/property/new') : undefined}
        />
      }
      renderItem={({ item }) => <PropertyCard property={item} />}
    />
  );
}

function SummaryStat({
  label,
  value,
  warn,
}: {
  label: string;
  value: string | number;
  warn?: boolean;
}) {
  return (
    <View style={[styles.stat, warn && styles.statWarn]}>
      <Text style={[styles.statValue, warn && styles.statValueWarn]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
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
    backgroundColor: theme.colors.surfaceMuted,
  },
  statWarn: { backgroundColor: theme.colors.warningLight },
  statValue: {
    fontSize: 18,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.3,
  },
  statValueWarn: { color: theme.colors.warning },
  statLabel: {
    fontSize: 11,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  cta: { marginBottom: theme.spacing.md },
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.sm },
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
