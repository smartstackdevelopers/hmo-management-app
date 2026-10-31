import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Alert, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { FavoriteButton } from '@/components/listings/FavoriteButton';
import { ListingThumb } from '@/components/listings/ListingPhotos';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatGBP, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useTabClearance } from '@/hooks/useLayout';
import { ListingItem } from '@/lib/api';
import { useListings } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { useTenantPreferences } from '@/hooks/useTenantPreferences';

type SortOption = 'best_match' | 'rent_asc' | 'rent_desc' | 'newest';
type FilterOption = 'all' | 'bills' | 'ensuite' | 'furnished' | 'saved';

const SORT_LABELS: Record<SortOption, string> = {
  best_match: 'Best',
  rent_asc: 'Rent ↑',
  rent_desc: 'Rent ↓',
  newest: 'Newest',
};

export default function BrowseScreen() {
  const bottomPad = useTabClearance();
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
    const q = query.trim().toLowerCase();
    if (q) {
      items = items.filter((item) => {
        const p = item.room?.property;
        return (
          item.title.toLowerCase().includes(q) ||
          p?.name.toLowerCase().includes(q) ||
          p?.city.toLowerCase().includes(q) ||
          p?.postcode.toLowerCase().includes(q)
        );
      });
    }
    if (filter === 'bills') items = items.filter((i) => i.billsIncluded);
    if (filter === 'ensuite') items = items.filter((i) => i.room?.ensuite);
    if (filter === 'furnished') items = items.filter((i) => i.room?.furnished);
    if (filter === 'saved') {
      const ids = new Set(favorites.map((f) => f.listingId));
      items = items.filter((i) => ids.has(i.id));
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

  return (
    <FlatList
      style={styles.container}
      data={listings}
      keyExtractor={(item) => item.id}
      contentContainerStyle={[
        listings.length === 0 ? styles.emptyList : styles.list,
        { paddingBottom: bottomPad },
      ]}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}
      ListHeaderComponent={
        <View style={styles.header}>
          <View style={styles.searchWrap}>
            <Ionicons name="search-outline" size={18} color={theme.colors.textMuted} style={styles.searchIcon} />
            <TextInput
              style={styles.searchInput}
              value={query}
              onChangeText={setQuery}
              placeholder="Area, postcode or property"
              placeholderTextColor={theme.colors.textMuted}
              returnKeyType="search"
            />
            {query.length > 0 && (
              <Pressable onPress={() => setQuery('')} hitSlop={8}>
                <Ionicons name="close-circle" size={18} color={theme.colors.textMuted} />
              </Pressable>
            )}
          </View>

          <View style={styles.chips}>
            {(['all', 'saved', 'bills', 'ensuite', 'furnished'] as FilterOption[]).map((f) => (
              <Pressable key={f} style={[styles.chip, filter === f && styles.chipActive]} onPress={() => setFilter(f)}>
                <Text style={[styles.chipText, filter === f && styles.chipTextActive]}>
                  {f === 'all' ? 'All' : f === 'saved' ? 'Saved' : f === 'bills' ? 'Bills' : f.charAt(0).toUpperCase() + f.slice(1)}
                </Text>
              </Pressable>
            ))}
          </View>

          <View style={styles.toolbar}>
            <Text style={styles.resultCount}>{listings.length} room{listings.length === 1 ? '' : 's'}</Text>
            <View style={styles.toolbarActions}>
              <Pressable onPress={handleSaveSearch} hitSlop={8}>
                <Text style={styles.link}>Save</Text>
              </Pressable>
              <Pressable onPress={() => router.push('/(app)/wishlist')} hitSlop={8}>
                <Text style={styles.link}>Wishlist</Text>
              </Pressable>
            </View>
          </View>

          <View style={styles.chips}>
            {(Object.keys(SORT_LABELS) as SortOption[]).map((s) => (
              <Pressable key={s} style={[styles.chip, sort === s && styles.chipActive]} onPress={() => setSort(s)}>
                <Text style={[styles.chipText, sort === s && styles.chipTextActive]}>{SORT_LABELS[s]}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title="No rooms found"
          message={query || filter !== 'all' ? 'Try a different search or filter.' : 'New rooms will show up here.'}
          icon="bed-outline"
        />
      }
      renderItem={({ item }) => (
        <ListingCard
          item={item}
          isFavorited={isFavorited(item.id)}
          onToggleFavorite={toggle}
        />
      )}
    />
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

function ListingCard({
  item,
  isFavorited,
  onToggleFavorite,
}: {
  item: ListingItem;
  isFavorited: boolean;
  onToggleFavorite: (listing: ListingItem) => void;
}) {
  const property = item.room?.property;
  const rent = item.room?.rentPcm ?? 0;
  const availableLabel = item.availableFrom ? `From ${formatUKDate(item.availableFrom)}` : 'Available now';

  return (
    <Card style={styles.card} padded={false} onPress={() => router.push(`/(app)/listing/${item.id}`)}>
      <ListingThumb photos={item.photos} listingId={item.id} />
      <View style={styles.cardBody}>
        <View style={styles.cardTop}>
          <View style={styles.cardHeader}>
            <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
            <Text style={styles.location} numberOfLines={1}>{property?.city} · {property?.postcode}</Text>
            <Text style={styles.available} numberOfLines={1}>{availableLabel}</Text>
          </View>
          <View style={styles.priceWrap}>
            <FavoriteButton listing={item} active={isFavorited} onToggle={onToggleFavorite} />
            <Text style={styles.rent}>{formatGBP(rent)}</Text>
            <Text style={styles.perMonth}>/pcm</Text>
          </View>
        </View>
        <View style={styles.tags}>
          {item.billsIncluded && <Badge label="Bills included" variant="success" />}
          {!item.billsIncluded && <Badge label="Bills separate" variant="default" />}
          <Badge label="No council tax" variant="info" />
          {item.room?.ensuite && <Badge label="Ensuite" variant="info" />}
          {item.room?.furnished && <Badge label="Furnished" variant="default" />}
        </View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  list: { padding: theme.spacing.md },
  emptyList: { flexGrow: 1, padding: theme.spacing.md },
  header: { marginBottom: theme.spacing.sm, width: '100%' },
  searchWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    paddingHorizontal: theme.spacing.sm,
    marginBottom: theme.spacing.sm,
    width: '100%',
  },
  searchIcon: { marginRight: 6 },
  searchInput: { flex: 1, minWidth: 0, paddingVertical: 12, fontSize: 15, color: theme.colors.text },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.sm },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: theme.radius.full,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
  },
  chipActive: { backgroundColor: theme.colors.accentLight, borderColor: theme.colors.secondary },
  chipText: { fontSize: 12, fontWeight: '600', color: theme.colors.textSecondary },
  chipTextActive: { color: theme.colors.secondary },
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
    gap: theme.spacing.sm,
    flexWrap: 'wrap',
  },
  toolbarActions: { flexDirection: 'row', gap: 16, flexShrink: 0 },
  resultCount: { fontSize: 13, color: theme.colors.textMuted, fontWeight: '600', flexShrink: 1 },
  link: { fontSize: 13, fontWeight: '600', color: theme.colors.secondary },
  card: { marginBottom: theme.spacing.sm, width: '100%', overflow: 'hidden' },
  cardBody: { padding: theme.spacing.md },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', gap: theme.spacing.md },
  cardHeader: { flex: 1, minWidth: 0 },
  title: { fontWeight: '700', fontSize: 16, color: theme.colors.text },
  location: { color: theme.colors.textMuted, fontSize: 13, marginTop: 4 },
  available: { color: theme.colors.textSecondary, fontSize: 13, marginTop: 4 },
  priceWrap: { alignItems: 'flex-end', flexShrink: 0 },
  rent: { fontWeight: '700', fontSize: 17, color: theme.colors.text, marginTop: 4 },
  perMonth: { color: theme.colors.textMuted, fontSize: 12 },
  tags: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: theme.spacing.sm, flexWrap: 'wrap' },
});
