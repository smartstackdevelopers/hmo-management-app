import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { FilterChips, InitialsTile, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { FavoriteButton } from '@/components/listings/FavoriteButton';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { ListingItem } from '@/lib/api';
import { useListings } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { useTenantPreferences } from '@/hooks/useTenantPreferences';

type SortOption = 'best_match' | 'rent_asc' | 'rent_desc' | 'newest';
type FilterOption = 'all' | 'bills' | 'ensuite' | 'furnished' | 'saved';

const SORTS: { id: SortOption; label: string }[] = [
  { id: 'best_match', label: 'Best' },
  { id: 'rent_asc', label: 'Rent low' },
  { id: 'rent_desc', label: 'Rent high' },
  { id: 'newest', label: 'Newest' },
];

const FILTERS: { id: FilterOption; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'saved', label: 'Saved' },
  { id: 'bills', label: 'Bills' },
  { id: 'ensuite', label: 'Ensuite' },
  { id: 'furnished', label: 'Furnished' },
];

export default function BrowseScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(ROUTE_ROLES.browse);
  if (guard) return guard;
  const params = useLocalSearchParams<{ q?: string; filter?: string; sort?: string }>();
  const { data, isLoading, error, refetch, isRefetching } = useListings();
  const { favorites, toggle, addSavedSearch, isFavorited } = useTenantPreferences();
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortOption>('best_match');
  const [filter, setFilter] = useState<FilterOption>('all');

  useEffect(() => {
    if (params.q) setQuery(params.q);
    if (params.filter && ['all', 'bills', 'ensuite', 'furnished', 'saved'].includes(params.filter)) {
      setFilter(params.filter as FilterOption);
    }
    if (params.sort && ['best_match', 'rent_asc', 'rent_desc', 'newest'].includes(params.sort)) {
      setSort(params.sort as SortOption);
    }
  }, [params.q, params.filter, params.sort]);

  const allListings = data?.listings ?? [];
  const averageRent = allListings.length
    ? allListings.reduce((sum, item) => sum + (item.room?.rentPcm ?? 0), 0) / allListings.length
    : 0;

  const listings = useMemo(() => {
    let items = [...allListings];
    const needle = query.trim().toLowerCase();
    if (needle) {
      items = items.filter((item) => {
        const property = item.room?.property;
        return (
          item.title.toLowerCase().includes(needle) ||
          (property?.name ?? '').toLowerCase().includes(needle) ||
          (property?.city ?? '').toLowerCase().includes(needle) ||
          (property?.postcode ?? '').toLowerCase().includes(needle) ||
          (property?.addressLine1 ?? '').toLowerCase().includes(needle)
        );
      });
    }
    if (filter === 'bills') items = items.filter((item) => item.billsIncluded);
    if (filter === 'ensuite') items = items.filter((item) => item.room?.ensuite);
    if (filter === 'furnished') items = items.filter((item) => item.room?.furnished);
    if (filter === 'saved') {
      const ids = new Set(favorites.map((favorite) => favorite.listingId));
      items = items.filter((item) => ids.has(item.id));
    }
    items.sort((a, b) => {
      if (sort === 'rent_asc') return (a.room?.rentPcm ?? 0) - (b.room?.rentPcm ?? 0);
      if (sort === 'rent_desc') return (b.room?.rentPcm ?? 0) - (a.room?.rentPcm ?? 0);
      if (sort === 'newest') {
        const aDate = a.createdAt ?? a.availableFrom ?? '';
        const bDate = b.createdAt ?? b.availableFrom ?? '';
        return new Date(bDate).getTime() - new Date(aDate).getTime();
      }
      return scoreListing(b, averageRent) - scoreListing(a, averageRent);
    });
    return items;
  }, [allListings, query, sort, filter, averageRent, favorites]);

  async function handleSaveSearch() {
    const label = query.trim() || filter !== 'all' ? `${query || filter} rooms` : 'All available rooms';
    await addSavedSearch({ label, query: query.trim(), filter, sort });
    Alert.alert('Search saved', 'You can find it under Saved on your Account.');
  }

  if (isLoading) return <LoadingScreen message="Finding rooms..." />;
  if (error) return <ErrorState message="Could not load rooms" onRetry={refetch} />;

  const filteredDown = query.trim().length > 0 || filter !== 'all';

  return (
    <View style={styles.screen}>
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <ListScreen
        data={listings}
        keyExtractor={(item) => item.id}
        refreshing={isRefetching}
        onRefresh={refetch}
        padded={false}
        contentContainerStyle={[styles.list, listings.length === 0 && styles.emptyList]}
        ListHeaderComponent={
          <View>
            <ScreenHeader
              title="Find a room"
              subtitle={`${allListings.length} available`}
              action={
                <Pressable onPress={handleSaveSearch} accessibilityRole="button" accessibilityLabel="Save search">
                  <Text style={styles.save}>Save</Text>
                </Pressable>
              }
            />
            <SearchField value={query} onChangeText={setQuery} placeholder="Area, postcode or property" />
            <FilterChips options={FILTERS} value={filter} onChange={(id) => setFilter(id as FilterOption)} />
            <FilterChips options={SORTS} value={sort} onChange={(id) => setSort(id as SortOption)} />
          </View>
        }
        ListEmptyComponent={
          <EmptyState
            title="No rooms found"
            message={filteredDown ? 'Try a different search or filter.' : 'New rooms will show up here.'}
            icon="bed-outline"
            actionLabel={filteredDown ? 'Clear filters' : undefined}
            onAction={
              filteredDown
                ? () => {
                    setQuery('');
                    setFilter('all');
                  }
                : undefined
            }
          />
        }
        renderItem={({ item }) => (
          <RoomRow item={item} saved={isFavorited(item.id)} onToggle={toggle} />
        )}
      />
    </View>
  );
}

function scoreListing(item: ListingItem, averageRent: number): number {
  let score = 0;
  if (item.billsIncluded) score += 3;
  if (item.room?.ensuite) score += 3;
  if (item.room?.furnished) score += 2;
  const rent = item.room?.rentPcm ?? 0;
  if (averageRent > 0 && rent <= averageRent) score += 2;
  const date = new Date(item.createdAt ?? item.availableFrom ?? 0).getTime();
  if (Date.now() - date < 1000 * 60 * 60 * 24 * 21) score += 1;
  return score;
}

function RoomRow({
  item,
  saved,
  onToggle,
}: {
  item: ListingItem;
  saved: boolean;
  onToggle: (listing: ListingItem) => void;
}) {
  const property = item.room?.property;
  const title = item.room?.name && property?.addressLine1 ? `${item.room.name} · ${property.addressLine1}` : item.title;
  const available = item.availableFrom ? formatUKDate(item.availableFrom) : null;
  const meta = [property?.city, property?.postcode, formatGBP(item.room?.rentPcm ?? 0), available].filter(Boolean).join(' · ');

  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/listing/${item.id}`)}>
      <View style={styles.row}>
        <InitialsTile name={property?.addressLine1 || item.title} size={42} />
        <View style={styles.copy}>
          <Text style={styles.title} numberOfLines={1}>{title}</Text>
          <Text style={styles.meta} numberOfLines={1}>{meta}</Text>
        </View>
        {item.billsIncluded ? <Chip label="Bills" tone="green" /> : null}
        <FavoriteButton listing={item} active={saved} onToggle={onToggle} />
        <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.colors.background, paddingTop: theme.spacing.sm },
  back: { flexDirection: 'row', alignItems: 'center', marginLeft: theme.spacing.md },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  list: { paddingHorizontal: theme.spacing.md },
  emptyList: { flexGrow: 1 },
  save: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 14 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary, marginTop: 2 },
});
