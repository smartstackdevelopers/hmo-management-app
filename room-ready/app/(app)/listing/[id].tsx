import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { FactGrid, HouseBanner, titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { FavoriteButton } from '@/components/listings/FavoriteButton';
import { ListingPhotoGallery } from '@/components/listings/ListingPhotos';
import { Button } from '@/components/ui/Button';
import { Chip, type Tone } from '@/components/ui/Chip';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useApplications, useApplyListing, useListing, useReviewApplication, useUpdateListing } from '@/hooks/useApi';
import { useTenantPreferences } from '@/hooks/useTenantPreferences';

function statusTone(status: string): Tone {
  if (status === 'active' || status === 'approved') return 'green';
  if (status === 'paused' || status === 'pending') return 'amber';
  if (status === 'rejected') return 'red';
  return 'gray';
}

export default function ListingDetailScreen() {
  useHideTabHeader();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user, hmore } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useListing(id);
  const { data: appsData, refetch: refetchApps } = useApplications();
  const apply = useApplyListing();
  const updateListing = useUpdateListing();
  const review = useReviewApplication();
  const { isFavorited, toggle } = useTenantPreferences();
  const [message, setMessage] = useState('');

  if (isLoading) return <LoadingScreen />;
  if (error || !data?.listing) return <ErrorState message="Listing not found" onRetry={refetch} />;

  const listing = data.listing;
  const property = listing.room?.property;
  const canManage = ['landlord', 'property_manager', 'admin'].includes(user?.role ?? '');
  const isTenant = user?.role === 'tenant';
  const related = (appsData?.applications ?? []).filter((app) => app.listing?.id === listing.id || app.listing?.id === id);
  const myApplication = isTenant ? related[0] : undefined;
  const hasActiveApplication = myApplication && ['pending', 'approved'].includes(myApplication.status);
  const pending = related.filter((app) => app.status === 'pending');
  const title = listing.room?.name && property?.addressLine1 ? `${listing.room.name} · ${property.addressLine1}` : listing.title;
  const photos = listing.photos;
  const availableAt = listing.availableFrom ? new Date(listing.availableFrom) : null;
  const availableKnown = !!availableAt && !Number.isNaN(availableAt.getTime());
  const availableLabel = !availableKnown
    ? null
    : availableAt!.getTime() <= Date.now()
      ? 'Available now'
      : formatUKDate(listing.availableFrom!);
  const subtitle = [
    listing.room?.ensuite ? 'Ensuite' : null,
    listing.room?.furnished ? 'Furnished' : null,
    listing.billsIncluded ? 'Bills included' : null,
  ]
    .filter(Boolean)
    .join(' · ');
  const rent = listing.room?.rentPcm;

  async function handleApply() {
    try {
      await apply.mutateAsync({ listingId: listing.id, message });
      Alert.alert('Application sent', 'The landlord will review it.');
      refetch();
      refetchApps();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Application failed');
    }
  }

  function reviewApplication(appId: string, tenantName: string, note?: string) {
    Alert.alert(tenantName, note || 'Review this application', [
      { text: 'Not now', style: 'cancel' },
      {
        text: 'Reject',
        style: 'destructive',
        onPress: () =>
          review.mutate(
            { id: appId, status: 'rejected' },
            { onSuccess: () => refetchApps(), onError: (err) => Alert.alert('Error', err instanceof Error ? err.message : 'Reject failed') },
          ),
      },
      {
        text: 'Approve',
        onPress: () =>
          review.mutate(
            { id: appId, status: 'approved' },
            { onSuccess: () => refetchApps(), onError: (err) => Alert.alert('Error', err instanceof Error ? err.message : 'Approve failed') },
          ),
      },
    ]);
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}
    >
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>

      {photos ? <ListingPhotoGallery photos={photos} listingId={listing.id} height={180} /> : <HouseBanner />}

      <View style={styles.titleRow}>
        <Text style={styles.title}>{title}</Text>
        {isTenant ? <FavoriteButton listing={listing} active={isFavorited(listing.id)} onToggle={toggle} /> : null}
      </View>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : listing.title !== title ? <Text style={styles.subtitle}>{listing.title}</Text> : null}
      <View style={styles.chips}>
        <Chip label={titleCase(listing.status)} tone={statusTone(listing.status)} />
        {availableLabel ? <Chip label={availableLabel} tone="green" /> : null}
        {typeof rent === 'number' ? <Chip label={`${formatGBP(rent)} / month`} tone="blue" /> : null}
        {myApplication ? <Chip label={titleCase(myApplication.status)} tone={statusTone(myApplication.status)} /> : null}
      </View>

      <FactGrid
        items={[
          { label: 'Size', value: listing.room?.sizeSqm ? `${listing.room.sizeSqm} m²` : '—' },
          { label: 'Furnished', value: listing.room ? (listing.room.furnished ? 'Yes' : 'No') : '—' },
          { label: 'Applications', value: hmore ? '—' : String(related.length) },
          { label: 'Listed', value: listing.createdAt ? formatUKDate(listing.createdAt) : '—' },
        ]}
      />

      {listing.description ? <Text style={styles.body}>{listing.description}</Text> : null}

      {canManage && (pending.length > 0 || listing.createdAt) ? (
        <View style={styles.enquiries}>
          <Text style={styles.section}>Enquiries</Text>
          {pending.map((app) => {
            const name = `${app.tenant?.firstName ?? ''} ${app.tenant?.lastName ?? ''}`.trim() || 'Applicant';
            return (
              <Pressable
                key={app.id}
                onPress={() => reviewApplication(app.id, name, app.message)}
                accessibilityRole="button"
                accessibilityLabel={`Application from ${name}`}
                style={styles.event}
              >
                <View style={styles.dot} />
                <Text style={styles.eventTitle} numberOfLines={1}>{`Application · ${name}`}</Text>
                <Text style={styles.eventDate}>{formatUKDate(app.createdAt)}</Text>
              </Pressable>
            );
          })}
          {listing.createdAt ? (
            <View style={styles.event}>
              <View style={[styles.dot, styles.dotMuted]} />
              <Text style={styles.eventTitle} numberOfLines={1}>
                {listing.status === 'active' ? 'Listing published' : 'Listing created'}
              </Text>
              <Text style={styles.eventDate}>{formatUKDate(listing.createdAt)}</Text>
            </View>
          ) : null}
        </View>
      ) : null}

      {isTenant && listing.status === 'active' && !hasActiveApplication ? (
        <View>
          <Input label="Message" value={message} onChangeText={setMessage} multiline placeholder="Optional note" />
          <Button title="Send application" onPress={handleApply} loading={apply.isPending} fullWidth size="lg" />
        </View>
      ) : null}

      {canManage ? (
        <Button
          title="Manage listing"
          accessibilityLabel={listing.status === 'active' ? 'Pause listing' : 'Activate listing'}
          onPress={() =>
            updateListing.mutate(
              { id: listing.id, status: listing.status === 'active' ? 'paused' : 'active' },
              { onSuccess: () => refetch() },
            )
          }
          loading={updateListing.isPending}
          fullWidth
          size="lg"
        />
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  back: { flexDirection: 'row', alignItems: 'center', marginBottom: theme.spacing.md, alignSelf: 'flex-start' },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  titleRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 },
  title: { flex: 1, fontSize: 26, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4 },
  subtitle: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22, marginBottom: theme.spacing.md },
  enquiries: { marginBottom: theme.spacing.md },
  section: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text, marginBottom: theme.spacing.sm },
  event: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 8, minHeight: 44 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: theme.colors.secondary },
  dotMuted: { backgroundColor: theme.colors.textMuted },
  eventTitle: { flex: 1, fontFamily: FONT_MEDIUM, color: theme.colors.text, fontSize: 14 },
  eventDate: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, fontSize: 12 },
});
