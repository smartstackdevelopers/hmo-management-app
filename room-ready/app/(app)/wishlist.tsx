import { router } from 'expo-router';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { FavoriteButton } from '@/components/listings/FavoriteButton';
import { ListingThumb } from '@/components/listings/ListingPhotos';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState, LoadingScreen } from '@/components/ui/States';
import { ROUTE_ROLES } from '@/constants/permissions';
import { formatGBP } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useListings } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { useTenantPreferences } from '@/hooks/useTenantPreferences';
import { ListingItem } from '@/lib/api';

export default function WishlistScreen() {
  const guard = useRoleGuard(ROUTE_ROLES.wishlist);
  if (guard) return guard;

  const { data, isLoading, refetch, isRefetching } = useListings();
  const { favorites, savedSearches, loading: prefsLoading, toggle, deleteSavedSearch, isFavorited } =
    useTenantPreferences();

  if (isLoading || prefsLoading) return <LoadingScreen message="Loading your wishlist..." />;

  const allListings = data?.listings ?? [];
  const wishlistListings = favorites
    .map((f) => allListings.find((l) => l.id === f.listingId))
    .filter((l): l is ListingItem => !!l);

  return (
    <FlatList
      style={styles.container}
      data={wishlistListings}
      keyExtractor={(item) => item.id}
      contentContainerStyle={wishlistListings.length === 0 ? styles.emptyList : styles.list}
      refreshControl={
        <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />
      }
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={styles.title}>Your wishlist</Text>
          <Text style={styles.subtitle}>Saved rooms and search alerts for rooms you want to revisit.</Text>

          {savedSearches.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>Saved searches</Text>
              {savedSearches.map((search) => (
                <Card key={search.id} style={styles.searchCard}>
                  <View style={styles.searchRow}>
                    <Ionicons name="notifications-outline" size={18} color={theme.colors.secondary} />
                    <View style={styles.searchCopy}>
                      <Text style={styles.searchLabel}>{search.label}</Text>
                      <Text style={styles.searchMeta}>
                        {search.query || 'Any area'} · {search.filter} · {search.sort}
                      </Text>
                    </View>
                    <Pressable onPress={() => deleteSavedSearch(search.id)} hitSlop={8}>
                      <Ionicons name="trash-outline" size={18} color={theme.colors.error} />
                    </Pressable>
                  </View>
                  <Pressable
                    onPress={() =>
                      router.push({
                        pathname: '/(app)/browse',
                        params: { q: search.query, filter: search.filter, sort: search.sort },
                      })
                    }
                  >
                    <Text style={styles.runSearch}>Run this search →</Text>
                  </Pressable>
                </Card>
              ))}
            </>
          )}

          <Text style={styles.sectionTitle}>
            Saved rooms ({wishlistListings.length})
          </Text>
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title="No saved rooms yet"
          message="Tap the heart on any listing while browsing to save it here."
          icon="heart-outline"
          actionLabel="Find rooms"
          onAction={() => router.push('/(app)/(tabs)/find' as never)}
        />
      }
      renderItem={({ item }) => (
        <Card style={styles.card} padded={false} onPress={() => router.push(`/(app)/listing/${item.id}`)}>
          <ListingThumb photos={item.photos} listingId={item.id} style={styles.wishThumb} />
          <View style={styles.cardRow}>
            <View style={styles.cardCopy}>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.cardMeta}>
                {item.room?.property?.city} · {formatGBP(item.room?.rentPcm ?? 0)}/pcm
              </Text>
              <View style={styles.tags}>
                {item.billsIncluded && <Badge label="Bills inc." variant="success" />}
                <Badge label="No council tax" variant="info" />
                {item.room?.ensuite && <Badge label="Ensuite" variant="info" />}
              </View>
            </View>
            <FavoriteButton listing={item} active={isFavorited(item.id)} onToggle={toggle} />
          </View>
        </Card>
      )}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  list: { padding: theme.spacing.md, paddingBottom: theme.spacing.xl },
  emptyList: { flexGrow: 1, padding: theme.spacing.md },
  header: { marginBottom: theme.spacing.sm },
  title: { ...theme.typography.h2, color: theme.colors.text },
  subtitle: { color: theme.colors.textMuted, fontSize: 14, marginTop: 4, marginBottom: theme.spacing.md },
  sectionTitle: { ...theme.typography.h3, color: theme.colors.text, marginTop: theme.spacing.md, marginBottom: theme.spacing.sm },
  searchCard: { marginBottom: theme.spacing.sm },
  searchRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  searchCopy: { flex: 1 },
  searchLabel: { fontWeight: '600', color: theme.colors.text },
  searchMeta: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2, textTransform: 'capitalize' },
  runSearch: { color: theme.colors.secondary, fontWeight: '600', fontSize: 13, marginTop: 10 },
  card: { marginBottom: theme.spacing.sm, overflow: 'hidden' },
  wishThumb: { height: 120 },
  cardRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, padding: theme.spacing.md },
  cardCopy: { flex: 1 },
  cardTitle: { fontWeight: '700', fontSize: 16, color: theme.colors.text },
  cardMeta: { color: theme.colors.textSecondary, marginTop: 4, fontSize: 14 },
  tags: { flexDirection: 'row', gap: 6, marginTop: 8, flexWrap: 'wrap' },
});
