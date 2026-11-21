import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Linking, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { FactGrid, HouseBanner, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { CouncilContactCard, CouncilStandardsBanner } from '@/components/compliance/CouncilStandardsBanner';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen, SectionHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { BIRMINGHAM_COUNCIL, isBirminghamPostcode, TENANT_RIGHTS_BIRMINGHAM } from '@/constants/birmingham';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP, formatUKDate } from '@/constants/uk';
import { TenantHousing } from '@/components/tenant/TenantHousing';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useApplications, useTenancies } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

function LegacyTenancyScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(TAB_ROLES.tenancy);
  if (guard) return guard;

  const { data, isLoading, error, refetch, isRefetching } = useTenancies();
  const { data: appsData } = useApplications();

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load tenancy details" onRetry={refetch} />;

  const tenancy = data?.tenancies?.find((t) => t.status === 'active') ?? data?.tenancies?.[0];
  const applications = appsData?.applications ?? [];
  const pendingApps = applications.filter((a) => a.status === 'pending');

  if (!tenancy) {
    return (
      <Screen refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}>
        {pendingApps.length > 0 ? (
          <>
            <SectionHeader title="Your applications" />
            {pendingApps.map((app) => (
              <Card key={app.id} style={styles.appCard} onPress={() => app.listing?.id && router.push(`/(app)/listing/${app.listing.id}`)}>
                <View style={styles.appRow}>
                  <Text style={styles.appTitle}>{app.listing?.title ?? 'Room application'}</Text>
                  <Badge label={app.status} variant="warning" />
                </View>
                <Text style={styles.appMeta}>
                  {app.listing?.room?.property?.city ?? 'UK'} · Applied {formatUKDate(app.createdAt)}
                </Text>
              </Card>
            ))}
            <Button title="Find more rooms" variant="outline" onPress={() => router.push('/(app)/(tabs)/find' as never)} fullWidth style={styles.browseBtn} />
            <Button title="View Wishlist" variant="outline" onPress={() => router.push('/(app)/wishlist')} fullWidth style={styles.browseBtn} />
          </>
        ) : (
          <EmptyState
            title="No active tenancy"
            message="Browse available rooms across the UK and apply directly through Room Ready."
            icon="home-outline"
            actionLabel="Find a Room"
            onAction={() => router.push('/(app)/(tabs)/find' as never)}
          />
        )}
      </Screen>
    );
  }

  const property = tenancy.room?.property;
  const isBirmingham = property?.postcode ? isBirminghamPostcode(property.postcode) : false;
  return (
    <Screen refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}>
      {isBirmingham && <CouncilStandardsBanner variant="compact" />}

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Back"
        onPress={() => (router.canGoBack() ? router.back() : router.push('/(app)/(tabs)'))}
        style={styles.back}
      >
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <HouseBanner />
      <View style={styles.header}>
        <Text style={styles.title}>{[tenancy.room?.name, property?.addressLine1 || property?.name].filter(Boolean).join(' · ')}</Text>
        <Badge label={tenancy.status === 'active' ? 'Active' : tenancy.status} variant={tenancy.status === 'active' ? 'success' : 'default'} format={false} />
      </View>
      <Text style={styles.address}>
        {[property?.city, property?.postcode].filter(Boolean).join(' · ')}
      </Text>
      <FactGrid
        items={[
          { label: 'Move-in', value: formatUKDate(tenancy.startDate) },
          { label: 'Rent', value: `${formatGBP(tenancy.rentPcm)} / month` },
          { label: 'Room', value: tenancy.room?.name || 'Not recorded' },
          { label: 'Deposit', value: formatGBP(tenancy.deposit) },
        ]}
      />
      <Button
        title="Message"
        onPress={() => router.push('/(app)/(tabs)/messages')}
        fullWidth
        size="lg"
        style={styles.viewProperty}
      />

      <Card style={styles.section}>
        <Text style={styles.sectionTitle}>Tenancy period</Text>
        <Text style={styles.body}>Started {formatUKDate(tenancy.startDate)}</Text>
        {tenancy.endDate && <Text style={styles.body}>Ends {formatUKDate(tenancy.endDate)}</Text>}
      </Card>

      {property?.houseRules && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>House rules</Text>
          <Text style={styles.body}>{property.houseRules}</Text>
        </Card>
      )}

      {property?.emergencyContact && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Emergency contact</Text>
          <Text style={styles.body}>{property.emergencyContact}</Text>
        </Card>
      )}

      {property?.hmoLicenceNumber && (
        <Card style={styles.licenceCard}>
          <Text style={styles.sectionTitle}>HMO licence</Text>
          <Text style={styles.licenceRef}>{property.hmoLicenceNumber}</Text>
          <Text style={styles.licenceNote}>Valid HMO licence required under the Housing Act 2004</Text>
        </Card>
      )}

      <Card style={styles.rightsCard}>
        <Text style={styles.sectionTitle}>Your rights as a tenant</Text>
        {TENANT_RIGHTS_BIRMINGHAM.map((right) => (
          <Text key={right} style={styles.rightItem}>• {right}</Text>
        ))}
        <Text style={styles.reportLink} onPress={() => Linking.openURL(BIRMINGHAM_COUNCIL.reportRepairUrl)}>
          Report housing hazards to {BIRMINGHAM_COUNCIL.name} →
        </Text>
      </Card>

      {isBirmingham && <CouncilContactCard />}
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { marginBottom: theme.spacing.lg, overflow: 'hidden' },
  cover: { width: '100%', height: 160, backgroundColor: theme.colors.surfaceMuted },
  heroBody: { padding: theme.spacing.md },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 },
  title: {
    flex: 1,
    fontSize: 20,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.3,
  },
  address: {
    color: theme.colors.textSecondary,
    marginTop: 8,
    lineHeight: 22,
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
  },
  viewProperty: { marginTop: theme.spacing.md },
  sectionLabel: {
    fontSize: 13,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: theme.spacing.sm,
  },
  stats: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.sm },
  stat: { flex: 1, alignItems: 'center', paddingVertical: theme.spacing.md },
  statVal: {
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    fontSize: 14,
    color: theme.colors.primary,
    textAlign: 'center',
  },
  statLbl: { fontSize: 11, color: theme.colors.textMuted, marginTop: 4, textAlign: 'center', fontFamily: FONT_MEDIUM },
  section: { marginBottom: theme.spacing.md },
  sectionTitle: { fontFamily: FONT_SEMIBOLD, fontWeight: '700', color: theme.colors.text, marginBottom: 8 },
  body: { color: theme.colors.textSecondary, lineHeight: 22, fontSize: 15, fontFamily: FONT_MEDIUM },
  licenceCard: { marginBottom: theme.spacing.md, backgroundColor: theme.colors.infoLight, borderColor: theme.colors.info },
  licenceRef: { fontSize: 16, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.secondary },
  licenceNote: { fontSize: 12, color: theme.colors.textMuted, marginTop: 4, fontFamily: FONT_MEDIUM },
  rightsCard: { marginBottom: theme.spacing.lg },
  rightItem: { fontSize: 14, color: theme.colors.textSecondary, lineHeight: 22, marginBottom: 4, fontFamily: FONT_MEDIUM },
  reportLink: { fontSize: 14, color: theme.colors.secondary, fontFamily: FONT_SEMIBOLD, fontWeight: '600', marginTop: 12 },
  appCard: { marginBottom: theme.spacing.sm },
  appRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  appTitle: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 15, color: theme.colors.text, flex: 1 },
  appMeta: { color: theme.colors.textMuted, fontSize: 13, marginTop: 4, fontFamily: FONT_MEDIUM },
  browseBtn: { marginTop: theme.spacing.md },
  back: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 2,
    marginBottom: 4,
    paddingRight: 8,
  },
  backText: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.secondaryDark },
});

export default function TenancyScreen() {
  const { hmore, user } = useAuth();
  if (hmore && user?.role === 'tenant') return <TenantHousing />;
  return <LegacyTenancyScreen />;
}
