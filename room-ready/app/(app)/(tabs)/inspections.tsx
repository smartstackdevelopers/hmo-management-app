import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { FilterChips, InitialsTile, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { InspectionItem } from '@/lib/api';
import { useInspections } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

type InspectionFilter = 'upcoming' | 'completed' | 'failed';

function bucket(status: string): InspectionFilter {
  const value = status.toLowerCase();
  if (value === 'completed' || value === 'passed') return 'completed';
  if (value.includes('fail') || value === 'cancelled') return 'failed';
  return 'upcoming';
}

function toneFor(status: string): Tone {
  const group = bucket(status);
  if (group === 'completed') return 'green';
  if (group === 'failed') return 'amber';
  return 'indigo';
}

function chipLabel(status: string): string {
  const value = status.toLowerCase();
  if (value === 'cancelled') return 'Cancelled';
  const group = bucket(status);
  if (group === 'completed') return 'Passed';
  if (group === 'failed') return 'Actions';
  return 'Booked';
}

export default function InspectionsScreen() {
  useHideTabHeader();
  const guard = useRoleGuard([...TAB_ROLES.inspections, 'landlord']);
  if (guard) return guard;

  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useInspections();
  const canSchedule = ['landlord', 'property_manager', 'admin'].includes(user?.role ?? '');
  const [filter, setFilter] = useState<InspectionFilter>('upcoming');
  const [query, setQuery] = useState('');

  const inspections = data?.inspections ?? [];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return inspections.filter((item) => {
      if (bucket(item.status) !== filter) return false;
      if (!needle) return true;
      const haystack = `${item.property?.name ?? ''} ${item.property?.addressLine1 ?? ''} ${item.property?.postcode ?? ''} ${item.notes ?? ''} ${item.status}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [inspections, filter, query]);

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load inspections" onRetry={refetch} />;

  return (
    <ListScreen
      data={filtered}
      keyExtractor={(item) => item.id}
      refreshing={isRefetching}
      onRefresh={refetch}
      contentContainerStyle={filtered.length === 0 ? styles.emptyList : undefined}
      ListHeaderComponent={
        <View>
          <ScreenHeader
            title="Inspections"
            subtitle={`${inspections.length} inspection${inspections.length === 1 ? '' : 's'}`}
            action={
              canSchedule ? (
                <Button title="Schedule" icon="add" size="sm" onPress={() => router.push('/(app)/inspection/new')} />
              ) : undefined
            }
          />
          <SearchField value={query} onChangeText={setQuery} placeholder="Search address" />
          <FilterChips
            options={[
              { id: 'upcoming', label: 'Upcoming' },
              { id: 'completed', label: 'Completed' },
              { id: 'failed', label: 'Failed' },
            ]}
            value={filter}
            onChange={(id) => setFilter(id as InspectionFilter)}
          />
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title={inspections.length === 0 ? 'No inspections' : 'Nothing in this filter'}
          message={
            inspections.length === 0
              ? 'Scheduled visits will show up here.'
              : 'Try another filter or a different address.'
          }
          icon="clipboard-outline"
          actionLabel={canSchedule && inspections.length === 0 ? 'Schedule inspection' : undefined}
          onAction={canSchedule && inspections.length === 0 ? () => router.push('/(app)/inspection/new') : undefined}
        />
      }
      renderItem={({ item }) => <InspectionCard item={item} />}
    />
  );
}

function visitWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return formatUKDate(iso);
  const time = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  return `${formatUKDate(iso)} · ${time}`;
}

function InspectionCard({ item }: { item: InspectionItem }) {
  const title = item.property?.addressLine1 || item.property?.name || 'Inspection';
  const meta = [visitWhen(item.scheduledAt), item.notes].filter(Boolean).join(' · ');
  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/inspection/${item.id}`)}>
      <View style={styles.row}>
        <InitialsTile name={title} size={42} />
        <View style={styles.copy}>
          <Text style={styles.title} numberOfLines={1}>{title}</Text>
          <Text style={styles.meta} numberOfLines={1}>{meta}</Text>
        </View>
        <Chip label={chipLabel(item.status)} tone={toneFor(item.status)} />
        <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  emptyList: { flexGrow: 1 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 15, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary, marginTop: 2 },
});
