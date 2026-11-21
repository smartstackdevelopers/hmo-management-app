import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { FilterChips, InitialsTile, SearchField, titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useApplications, useListings } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

type ListingFilter = 'all' | 'active' | 'paused' | 'applications';

type Row = {
  id: string;
  name: string;
  title: string;
  meta: string;
  chip: string;
  tone: Tone;
  onPress: () => void;
};

function statusTone(status: string): Tone {
  if (status === 'active') return 'green';
  if (status === 'paused') return 'gray';
  if (status === 'pending') return 'amber';
  return 'indigo';
}

export default function ListingsScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(TAB_ROLES.listings);
  if (guard) return guard;

  const { data: listingsData, isLoading: l1, error: e1, refetch: r1, isRefetching: rf1 } = useListings(true);
  const { data: appsData, isLoading: l2, error: e2, refetch: r2, isRefetching: rf2 } = useApplications();
  const [filter, setFilter] = useState<ListingFilter>('all');
  const [query, setQuery] = useState('');

  const listings = listingsData?.listings ?? [];
  const pending = (appsData?.applications ?? []).filter((app) => app.status === 'pending');

  const rows = useMemo<Row[]>(() => {
    const needle = query.trim().toLowerCase();
    if (filter === 'applications') {
      return pending
        .filter((app) => {
          if (!needle) return true;
          const name = `${app.tenant?.firstName ?? ''} ${app.tenant?.lastName ?? ''}`;
          return `${name} ${app.listing?.title ?? ''} ${app.message ?? ''}`.toLowerCase().includes(needle);
        })
        .map((app) => {
          const name = `${app.tenant?.firstName ?? ''} ${app.tenant?.lastName ?? ''}`.trim() || 'Applicant';
          return {
            id: app.id,
            name,
            title: name,
            meta: [app.listing?.title, app.message].filter(Boolean).join(' · ') || 'Application',
            chip: titleCase(app.status),
            tone: statusTone(app.status),
            onPress: () => {
              if (app.listing?.id) router.push(`/(app)/listing/${app.listing.id}`);
            },
          };
        });
    }
    return listings
      .filter((item) => {
        if (filter === 'active' && item.status !== 'active') return false;
        if (filter === 'paused' && item.status !== 'paused') return false;
        if (!needle) return true;
        return `${item.title} ${item.room?.property?.name ?? ''} ${item.room?.name ?? ''}`.toLowerCase().includes(needle);
      })
      .map((item) => ({
        id: item.id,
        name: item.room?.property?.addressLine1 || item.title,
        title: item.title,
        meta: [item.room?.property?.name, item.room?.name, formatGBP(item.room?.rentPcm ?? 0)].filter(Boolean).join(' · '),
        chip: titleCase(item.status),
        tone: statusTone(item.status),
        onPress: () => router.push(`/(app)/listing/${item.id}`),
      }));
  }, [filter, listings, pending, query]);

  if (l1 || l2) return <LoadingScreen message="Loading listings..." />;
  if (e1 || e2) return <ErrorState message="Could not load listings" onRetry={() => { r1(); r2(); }} />;

  const chips: { id: ListingFilter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'active', label: 'Active' },
    { id: 'paused', label: 'Paused' },
    { id: 'applications', label: 'Applications' },
  ];
  const sourceEmpty = filter === 'applications' ? pending.length === 0 && listings.length === 0 : listings.length === 0;

  return (
    <ListScreen
      data={rows}
      keyExtractor={(item) => item.id}
      refreshing={rf1 || rf2}
      onRefresh={() => { r1(); r2(); }}
      contentContainerStyle={rows.length === 0 ? styles.emptyList : undefined}
      ListHeaderComponent={
        <View>
          <ScreenHeader
            title="Listings"
            subtitle={`${listings.length} listing${listings.length === 1 ? '' : 's'}`}
            action={<Button title="Properties" size="sm" variant="outline" onPress={() => router.push('/(app)/(tabs)/properties')} />}
          />
          <SearchField value={query} onChangeText={setQuery} placeholder="Search listings" />
          <FilterChips options={chips} value={filter} onChange={(id) => setFilter(id as ListingFilter)} />
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title={sourceEmpty ? 'No listings yet' : 'Nothing in this filter'}
          message={
            sourceEmpty
              ? 'Create a listing from a vacant room.'
              : 'Try another filter or search.'
          }
          icon="list-outline"
          actionLabel={sourceEmpty ? 'Go to properties' : undefined}
          onAction={sourceEmpty ? () => router.push('/(app)/(tabs)/properties') : undefined}
        />
      }
      renderItem={({ item }) => (
        <Card style={styles.card} onPress={item.onPress}>
          <View style={styles.row}>
            <InitialsTile name={item.name} size={42} />
            <View style={styles.copy}>
              <Text style={styles.title} numberOfLines={1}>{item.title}</Text>
              <Text style={styles.meta} numberOfLines={1}>{item.meta}</Text>
            </View>
            <Chip label={item.chip} tone={item.tone} />
            <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
          </View>
        </Card>
      )}
    />
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
