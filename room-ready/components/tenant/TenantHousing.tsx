import { useQuery } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { FactGrid, HouseBanner, titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { orNull, useConnectivity } from '@/components/tenant/safeFetch';
import { TenantLoadError, TenantOffline } from '@/components/tenant/TenantStates';
import { shortDate } from '@/components/tenant/tenantFormat';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Screen } from '@/components/ui/Screen';
import { Section } from '@/components/ui/Section';
import { EmptyState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { listDocuments } from '@/lib/hmore/services/documents';
import { formatAssignedAddress, getOwnHousing } from '@/lib/hmore/services/housing';
import { listHousingApplications } from '@/lib/hmore/services/housingApplications';
import { listMyRentObligations, type RentObligation } from '@/lib/hmore/services/tenants/rentPayments';

function rentFact(rows: RentObligation[] | null | undefined, fallback: string): string {
  if (!rows || rows.length === 0) return fallback;
  const next = [...rows].sort((a, b) => {
    const ad = a.due_date ? new Date(a.due_date).getTime() : Number.POSITIVE_INFINITY;
    const bd = b.due_date ? new Date(b.due_date).getTime() : Number.POSITIVE_INFINITY;
    return ad - bd;
  })[0];
  if (!next) return fallback;
  const status = next.payment_status?.trim() ? titleCase(next.payment_status) : '';
  const due = shortDate(next.due_date);
  if (status && due) return `${status} · ${due}`;
  return status || due || fallback;
}

export function TenantHousing() {
  useHideTabHeader();
  const { t, fontScale, prefs } = useI18n();
  const net = useConnectivity();
  const housingQuery = useQuery({
    queryKey: ['hmore', 'tenant-housing'],
    queryFn: getOwnHousing,
  });
  const appsQuery = useQuery({
    queryKey: ['hmore', 'housing-applications'],
    queryFn: listHousingApplications,
  });
  const rentQuery = useQuery({
    queryKey: ['hmore', 'rent-obligations'],
    queryFn: () => orNull(() => listMyRentObligations()),
  });
  const docsQuery = useQuery({
    queryKey: ['hmore', 'documents', 'tenant-home'],
    queryFn: () => orNull(() => listDocuments()),
  });

  const loading = (housingQuery.isLoading && housingQuery.data === undefined) || (appsQuery.isLoading && !appsQuery.data);
  const error = housingQuery.error ?? appsQuery.error;
  const offline = net.data === 'offline';
  if (loading && housingQuery.data === undefined && !appsQuery.data) {
    if (offline) return <TenantOffline />;
    return <LoadingScreen message={t('housing.loading')} />;
  }
  if (error && housingQuery.data === undefined) {
    if (offline) return <TenantOffline />;
    return (
      <TenantLoadError
        title={t('housing.error')}
        onRetry={() => {
          housingQuery.refetch();
          appsQuery.refetch();
        }}
      />
    );
  }

  const housing = housingQuery.data;
  const applications = appsQuery.data?.items ?? [];
  const address = housing ? formatAssignedAddress(housing) : '';
  const contrast = prefs.highContrast;
  const missing = t('housing.notRecorded');
  const locality = [housing?.property?.city, housing?.property?.postcode].filter(Boolean).join(' · ');
  const title =
    [housing?.room?.label, housing?.property?.address_line1 || housing?.property?.name || address].filter(Boolean).join(' · ') ||
    t('housing.property');
  const history = (docsQuery.data?.items ?? [])
    .filter((item) => item.title?.trim())
    .slice(0, 6);

  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={
        <RefreshControl
          refreshing={housingQuery.isRefetching || appsQuery.isRefetching || rentQuery.isRefetching || docsQuery.isRefetching}
          onRefresh={() => {
            housingQuery.refetch();
            appsQuery.refetch();
            rentQuery.refetch();
            docsQuery.refetch();
            net.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('housing.back')}
        onPress={() => (router.canGoBack() ? router.back() : router.push('/(app)/(tabs)'))}
        style={styles.back}
      >
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>{t('housing.back')}</Text>
      </Pressable>

      {!housing ? (
        <EmptyState title={t('housing.noProfileTitle')} message={t('housing.noProfile')} icon="home-outline" />
      ) : (
        <View>
          <HouseBanner />
          <Text style={[styles.name, contrast && styles.contrastText, { fontSize: 22 * fontScale }]}>{title}</Text>
          {locality ? <Text style={[styles.address, { fontSize: 14 * fontScale }]}>{locality}</Text> : null}
          {!address && !locality ? <Text style={styles.unassigned}>{t('housing.unassigned')}</Text> : null}
          <View style={styles.chips}>
            <Chip
              label={housing.status === 'active' ? t('housing.tenancyActive') : titleCase(housing.status || t('housing.notRecorded'))}
              tone={housing.status === 'active' ? 'green' : 'gray'}
            />
            {housing.tenancy_reference ? <Chip label={housing.tenancy_reference} tone="blue" /> : null}
          </View>
          <FactGrid
            items={[
              { label: t('housing.moveIn'), value: missing },
              { label: t('housing.rent'), value: rentFact(rentQuery.data, missing) },
              { label: t('housing.landlord'), value: missing },
              { label: t('housing.deposit'), value: missing },
            ]}
          />
          <Section title={t('housing.history')}>
            {history.length === 0 ? (
              <Text style={styles.empty}>{missing}</Text>
            ) : (
              history.map((item, index) => (
                <View key={item.id} style={styles.historyRow}>
                  <View style={[styles.dot, index > 0 && styles.dotMuted]} />
                  <Text style={styles.historyTitle} numberOfLines={2}>
                    {item.title}
                  </Text>
                  <Text style={styles.historyDate}>{shortDate(item.updated_at || item.created_at)}</Text>
                </View>
              ))
            )}
          </Section>
          <Button
            title={t('housing.contactLandlord')}
            accessibilityLabel={t('housing.contactLandlord')}
            onPress={() => router.push('/(app)/notifications')}
            fullWidth
            size="lg"
            style={styles.contact}
          />
        </View>
      )}

      {applications.length > 0 ? (
        <Section title={t('housing.applications')}>
          {applications.map((app) => (
            <Card key={app.id} style={[styles.app, contrast ? styles.contrastCard : undefined]}>
              <View style={styles.header}>
                <Text style={styles.appTitle}>{app.reference_number}</Text>
                <Chip label={titleCase(app.status)} tone={app.status === 'active' ? 'green' : 'gray'} />
              </View>
              <Text style={styles.body}>{app.housing_requirements}</Text>
              <Text style={styles.meta}>
                {app.accommodation_type || t('housing.accommodationUnset')}
                {app.submitted_at ? ` · ${t('housing.submitted')} ${formatUKDate(app.submitted_at)}` : ''}
              </Text>
              {app.on_waiting_list ? (
                <Text style={styles.meta}>
                  {t('housing.waiting')}
                  {app.waiting_list_position ? ` · ${t('housing.position')} ${app.waiting_list_position}` : ''}
                </Text>
              ) : null}
              {app.information_required_notes ? (
                <Text style={styles.warn}>
                  {t('housing.information')}: {app.information_required_notes}
                </Text>
              ) : null}
            </Card>
          ))}
        </Section>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastCard: { borderWidth: 2, borderColor: '#000000' },
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
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 8 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.3 },
  address: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4, marginBottom: 10 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10, marginBottom: theme.spacing.md },
  contact: { marginBottom: theme.spacing.lg },
  unassigned: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginTop: 12 },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  historyRow: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 44 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: theme.colors.secondary },
  dotMuted: { backgroundColor: theme.colors.textMuted },
  historyTitle: { flex: 1, fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  historyDate: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary },
  app: { marginBottom: theme.spacing.sm },
  appTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text, flex: 1 },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
  warn: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.warning, marginTop: 8 },
});
