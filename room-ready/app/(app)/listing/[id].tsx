import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { FavoriteButton } from '@/components/listings/FavoriteButton';
import { ListingPhotoGallery } from '@/components/listings/ListingPhotos';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatGBP, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useApplyListing, useApplications, useListing, useUpdateListing } from '@/hooks/useApi';
import { useTenantPreferences } from '@/hooks/useTenantPreferences';

export default function ListingDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useListing(id);
  const { data: appsData } = useApplications();
  const apply = useApplyListing();
  const updateListing = useUpdateListing();
  const { isFavorited, toggle } = useTenantPreferences();
  const [message, setMessage] = useState('');

  if (isLoading) return <LoadingScreen />;
  if (error || !data) return <ErrorState message="Listing not found" onRetry={refetch} />;

  const listing = data.listing;
  const property = listing.room?.property;
  const canManage = ['landlord', 'property_manager', 'admin'].includes(user?.role ?? '');
  const isTenant = user?.role === 'tenant';
  const myApplication = isTenant
    ? (appsData?.applications ?? []).find((a) => a.listing?.id === listing.id || a.listing?.id === id)
    : undefined;
  const hasActiveApplication = myApplication && ['pending', 'approved'].includes(myApplication.status);

  async function handleApply() {
    try {
      await apply.mutateAsync({ listingId: listing.id, message });
      Alert.alert('Application sent', 'The landlord will review it shortly.');
      refetch();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Application failed');
    }
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}
    >
      <ListingPhotoGallery photos={listing.photos} listingId={listing.id} height={240} />

      <Card style={styles.hero}>
        <View style={styles.heroTop}>
          <Text style={styles.title}>{listing.title}</Text>
          {isTenant && (
            <FavoriteButton
              listing={listing}
              active={isFavorited(listing.id)}
              onToggle={toggle}
              size={26}
            />
          )}
        </View>
        <Text style={styles.address}>
          {property?.addressLine1}, {property?.city} {property?.postcode}
        </Text>
        <Text style={styles.rent}>
          {formatGBP(listing.room?.rentPcm ?? 0)}
          <Text style={styles.perMonth}> / month rent</Text>
        </Text>
        <View style={styles.tags}>
          {listing.billsIncluded && <Badge label="Bills included" variant="success" />}
          {!listing.billsIncluded && <Badge label="Bills separate" variant="default" />}
          <Badge label="No council tax" variant="info" />
          {listing.room?.ensuite && <Badge label="Ensuite" variant="info" />}
          {listing.room?.furnished && <Badge label="Furnished" variant="default" />}
          {listing.availableFrom && (
            <Badge label={`From ${formatUKDate(listing.availableFrom)}`} variant="default" />
          )}
        </View>
      </Card>

      <Card style={styles.section}>
        <Text style={styles.sectionTitle}>What you pay</Text>
        <View style={styles.costRow}>
          <Text style={styles.costLabel}>Room rent</Text>
          <Text style={styles.costValue}>{formatGBP(listing.room?.rentPcm ?? 0)} / month</Text>
        </View>
        <View style={styles.costRow}>
          <Text style={styles.costLabel}>Deposit</Text>
          <Text style={styles.costValue}>{formatGBP(listing.room?.deposit ?? 0)}</Text>
        </View>
        <View style={styles.costRow}>
          <Text style={styles.costLabel}>Bills (gas, electric, water, internet)</Text>
          <Text style={styles.costValue}>{listing.billsIncluded ? 'Included' : 'Not included'}</Text>
        </View>
        <View style={[styles.costRow, styles.costRowLast]}>
          <Text style={styles.costLabel}>Council tax</Text>
          <Text style={styles.costValue}>Landlord pays</Text>
        </View>
        <Text style={styles.costHint}>
          In licensed HMOs, council tax is usually paid by the landlord — not by individual tenants. You rent a room, not the whole property.
        </Text>
      </Card>

      {isTenant && listing.status === 'active' && hasActiveApplication && myApplication && (
        <Card style={styles.statusCard}>
          <Text style={styles.sectionTitle}>Your application</Text>
          <Badge
            label={myApplication.status}
            variant={myApplication.status === 'approved' ? 'success' : myApplication.status === 'rejected' ? 'error' : 'warning'}
          />
          <Text style={styles.statusHint}>
            {myApplication.status === 'pending' && 'Waiting for the landlord to review.'}
            {myApplication.status === 'approved' && 'Approved — the landlord will be in touch.'}
            {myApplication.status === 'rejected' && 'Not selected this time.'}
          </Text>
          {myApplication.status === 'rejected' && (
            <Button title="Find other rooms" variant="outline" onPress={() => router.push('/(app)/(tabs)/find' as never)} fullWidth style={styles.browseBtn} />
          )}
        </Card>
      )}

      {isTenant && listing.status === 'active' && !hasActiveApplication && (
        <Card style={styles.apply}>
          <Text style={styles.sectionTitle}>Apply for this room</Text>
          <Input
            label="Message (optional)"
            value={message}
            onChangeText={setMessage}
            multiline
            placeholder="A short note about yourself"
          />
          <Button title="Send application" onPress={handleApply} loading={apply.isPending} fullWidth size="lg" variant="accent" />
        </Card>
      )}

      {listing.description ? (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          <Text style={styles.body}>{listing.description}</Text>
        </Card>
      ) : null}

      {property?.id && (
        <Pressable onPress={() => router.push(`/(app)/property/${property.id}`)} style={styles.propertyLink}>
          <Text style={styles.propertyLinkText}>View property details</Text>
        </Pressable>
      )}

      {canManage && (
        <Card style={styles.apply}>
          <Text style={styles.sectionTitle}>Manage listing</Text>
          <Button
            title={listing.status === 'active' ? 'Pause listing' : 'Activate listing'}
            variant="secondary"
            onPress={() =>
              updateListing.mutate(
                { id: listing.id, status: listing.status === 'active' ? 'paused' : 'active' },
                { onSuccess: () => refetch() }
              )
            }
            loading={updateListing.isPending}
            fullWidth
          />
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 40 },
  hero: { borderColor: theme.colors.border },
  heroTop: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 },
  title: { ...theme.typography.h1, color: theme.colors.text, flex: 1 },
  address: { color: theme.colors.textSecondary, marginTop: 8, fontSize: 15, lineHeight: 22 },
  rent: { fontSize: 28, fontWeight: '700', color: theme.colors.text, marginTop: 14, letterSpacing: -0.5 },
  perMonth: { fontSize: 16, fontWeight: '500', color: theme.colors.textMuted },
  tags: { flexDirection: 'row', gap: 8, marginTop: 14, flexWrap: 'wrap' },
  costRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderLight,
  },
  costRowLast: { borderBottomWidth: 0 },
  costLabel: { flex: 1, fontSize: 14, color: theme.colors.textSecondary, lineHeight: 20 },
  costValue: { fontSize: 14, fontWeight: '600', color: theme.colors.text, textAlign: 'right' },
  costHint: {
    marginTop: 8,
    fontSize: 13,
    lineHeight: 19,
    color: theme.colors.textMuted,
  },
  propertyLink: { marginTop: theme.spacing.lg, paddingVertical: 8 },
  propertyLinkText: { color: theme.colors.secondary, fontWeight: '600', fontSize: 15 },
  section: { marginTop: theme.spacing.lg },
  sectionTitle: { fontWeight: '700', marginBottom: 8, fontSize: 16 },
  body: { color: theme.colors.textSecondary, lineHeight: 24, fontSize: 15 },
  apply: { marginTop: theme.spacing.lg },
  statusCard: { marginTop: theme.spacing.lg, backgroundColor: theme.colors.infoLight, borderColor: theme.colors.info },
  statusHint: { color: theme.colors.textSecondary, lineHeight: 22, fontSize: 14, marginTop: 10 },
  browseBtn: { marginTop: 12 },
});
