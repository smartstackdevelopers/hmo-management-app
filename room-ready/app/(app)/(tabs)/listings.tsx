import { router } from 'expo-router';
import { Alert, FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { ListingThumb } from '@/components/listings/ListingPhotos';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useTabClearance } from '@/hooks/useLayout';
import { ApplicationItem, ListingItem } from '@/lib/api';
import { useApplications, useListings, useReviewApplication, useUpdateListing } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function ListingsScreen() {
  const bottomPad = useTabClearance();
  const guard = useRoleGuard(TAB_ROLES.listings);
  if (guard) return guard;

  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const { data: listingsData, isLoading: l1, error: e1, refetch: r1, isRefetching: rf1 } = useListings(true);
  const { data: appsData, isLoading: l2, error: e2, refetch: r2, isRefetching: rf2 } = useApplications();
  const review = useReviewApplication();
  const updateListing = useUpdateListing();

  if (l1 || l2) return <LoadingScreen message="Loading listings..." />;
  if (e1 || e2) return <ErrorState message="Could not load listings" onRetry={() => { r1(); r2(); }} />;

  const listings = listingsData?.listings ?? [];
  const pendingApps = (appsData?.applications ?? []).filter((a) => a.status === 'pending');
  const activeCount = listings.filter((l) => l.status === 'active').length;
  const pausedCount = listings.filter((l) => l.status === 'paused').length;

  async function handleToggleStatus(listing: ListingItem) {
    const next = listing.status === 'active' ? 'paused' : 'active';
    try {
      await updateListing.mutateAsync({ id: listing.id, status: next });
      r1();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Update failed');
    }
  }

  function handleReview(appId: string, status: 'approved' | 'rejected', tenantName: string) {
    const action = status === 'approved' ? 'Approve' : 'Reject';
    const confirm = () => {
      review.mutate(
        { id: appId, status },
        {
          onSuccess: () => { r1(); r2(); },
          onError: (err) => Alert.alert('Error', err instanceof Error ? err.message : `${action} failed`),
        },
      );
    };
    if (status === 'rejected') {
      Alert.alert('Reject application', `Reject ${tenantName}'s application?`, [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Reject', style: 'destructive', onPress: confirm },
      ]);
    } else {
      confirm();
    }
  }

  return (
    <FlatList
      style={styles.container}
      data={listings}
      keyExtractor={(item) => item.id}
      contentContainerStyle={[styles.list, { paddingBottom: bottomPad }, listings.length === 0 && styles.emptyList]}
      refreshControl={<RefreshControl refreshing={rf1 || rf2} onRefresh={() => { r1(); r2(); }} tintColor={theme.colors.secondary} />}
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={styles.pageTitle}>Room listings</Text>
          <Text style={styles.pageSub}>Advertise vacant rooms and review applications.</Text>

          <View style={styles.summary}>
            <SummaryStat label="Active" value={activeCount} tone="success" />
            <SummaryStat label="Paused" value={pausedCount} />
            <SummaryStat label="Applications" value={pendingApps.length} tone={pendingApps.length > 0 ? 'warning' : undefined} />
          </View>

          {pendingApps.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.heading}>Pending applications</Text>
              {pendingApps.map((app) => (
                <ApplicationCard
                  key={app.id}
                  app={app}
                  busy={review.isPending}
                  onApprove={() => handleReview(app.id, 'approved', `${app.tenant?.firstName ?? 'Tenant'}`)}
                  onReject={() => handleReview(app.id, 'rejected', `${app.tenant?.firstName ?? 'Tenant'}`)}
                />
              ))}
            </View>
          )}

          {listings.length > 0 && <Text style={styles.heading}>Your listings</Text>}
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title="No listings yet"
          message="Add rooms to your properties, then create listings for available rooms."
          icon="list-outline"
          actionLabel="Go to Properties"
          onAction={() => router.push('/(app)/(tabs)/properties')}
        />
      }
      renderItem={({ item }) => (
        <ListingCard
          item={item}
          isAdmin={isAdmin}
          onPress={() => router.push(`/(app)/listing/${item.id}`)}
          onToggle={() => handleToggleStatus(item)}
          toggling={updateListing.isPending}
        />
      )}
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
  tone?: 'success' | 'warning';
}) {
  const bg =
    tone === 'success'
      ? theme.colors.successLight
      : tone === 'warning'
        ? theme.colors.warningLight
        : theme.colors.surfaceMuted;
  const color =
    tone === 'success'
      ? theme.colors.success
      : tone === 'warning'
        ? theme.colors.warning
        : theme.colors.text;

  return (
    <View style={[styles.stat, { backgroundColor: bg }]}>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function ApplicationCard({
  app,
  busy,
  onApprove,
  onReject,
}: {
  app: ApplicationItem;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <Card style={styles.appCard}>
      <Badge label="Pending" variant="warning" format={false} />
      <Text style={styles.appTitle}>{app.listing?.title}</Text>
      <Text style={styles.appTenant}>
        {app.tenant?.firstName} {app.tenant?.lastName} · {app.tenant?.email}
      </Text>
      {app.message && <Text style={styles.appMsg}>{app.message}</Text>}
      <View style={styles.appActions}>
        <Button title="Approve" size="sm" onPress={onApprove} disabled={busy} style={styles.appBtn} />
        <Button title="Reject" size="sm" variant="outline" onPress={onReject} disabled={busy} style={styles.appBtn} />
      </View>
    </Card>
  );
}

function ListingCard({
  item,
  isAdmin,
  onPress,
  onToggle,
  toggling,
}: {
  item: ListingItem;
  isAdmin: boolean;
  onPress: () => void;
  onToggle: () => void;
  toggling: boolean;
}) {
  return (
    <Card style={styles.card} padded={false}>
      <Pressable onPress={onPress}>
        <ListingThumb photos={item.photos} listingId={item.id} style={styles.thumb} />
        <View style={styles.cardBody}>
          <View style={styles.row}>
            <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
            <Badge label={item.status} variant={item.status === 'active' ? 'success' : 'default'} />
          </View>
          <Text style={styles.meta} numberOfLines={2}>
            {item.room?.property?.name} · {item.room?.name} · {formatGBP(item.room?.rentPcm ?? 0)}/pcm
          </Text>
          {!isAdmin && (
            <Pressable onPress={onToggle} disabled={toggling} style={toggling && styles.btnDisabled}>
              <Text style={styles.toggleText}>
                {item.status === 'active' ? 'Pause listing' : 'Activate listing'}
              </Text>
            </Pressable>
          )}
        </View>
      </Pressable>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  list: { padding: theme.spacing.md },
  emptyList: { flexGrow: 1 },
  header: { marginBottom: theme.spacing.sm },
  pageTitle: {
    fontSize: 26,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.4,
  },
  pageSub: {
    color: theme.colors.textSecondary,
    fontSize: 14,
    marginTop: 4,
    marginBottom: theme.spacing.md,
    fontFamily: FONT_MEDIUM,
  },
  summary: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.lg },
  stat: {
    flex: 1,
    borderRadius: theme.radius.lg,
    paddingVertical: 12,
    alignItems: 'center',
  },
  statValue: { fontSize: 20, fontFamily: FONT_BOLD, fontWeight: '700' },
  statLabel: { fontSize: 11, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 },
  section: { marginBottom: theme.spacing.lg },
  heading: {
    fontSize: 15,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '700',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  appCard: { marginBottom: theme.spacing.sm },
  appTitle: {
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    marginTop: 8,
    fontSize: 15,
  },
  appTenant: { color: theme.colors.textSecondary, marginTop: 4, fontFamily: FONT_MEDIUM, fontSize: 13 },
  appMsg: { color: theme.colors.textMuted, marginTop: 8, fontFamily: FONT_MEDIUM, lineHeight: 19 },
  appActions: { flexDirection: 'row', gap: 10, marginTop: 12 },
  appBtn: { flex: 1 },
  btnDisabled: { opacity: 0.5 },
  card: { marginBottom: theme.spacing.sm, overflow: 'hidden' },
  thumb: { height: 140 },
  cardBody: { padding: theme.spacing.md },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
  title: {
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    flex: 1,
    minWidth: 0,
    fontSize: 15,
  },
  meta: { color: theme.colors.textSecondary, marginTop: 4, fontFamily: FONT_MEDIUM, fontSize: 13 },
  toggleText: {
    color: theme.colors.secondary,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    fontSize: 14,
    marginTop: 10,
  },
});
