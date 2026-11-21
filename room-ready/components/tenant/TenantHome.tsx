import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { RefreshControl, StyleSheet, Text, View } from 'react-native';

import { ActivityRow } from '@/components/tenant/ActivityRow';
import { DAILY_HREF } from '@/components/tenant/tenantLinks';
import { orNull, useConnectivity } from '@/components/tenant/safeFetch';
import { TenantLoadError, TenantOffline } from '@/components/tenant/TenantStates';
import { shortDate, shortTime } from '@/components/tenant/tenantFormat';
import { StatTiles, shortWeekday, titleCase } from '@/components/dashboard/mobileChrome';
import { repairStatusText, repairStatusTone } from '@/components/maintenance/repairTone';
import { HeroCard } from '@/components/ui/HeroCard';
import { Avatar } from '@/components/ui/ListRow';
import { QuickActions } from '@/components/ui/QuickActions';
import { Screen } from '@/components/ui/Screen';
import { Section } from '@/components/ui/Section';
import { LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { listInbox } from '@/lib/hmore/services/communications';
import { formatAssignedAddress, getOwnHousing } from '@/lib/hmore/services/housing';
import { listMaintenance } from '@/lib/hmore/services/maintenance';
import { listMyRentObligations, type RentObligation } from '@/lib/hmore/services/tenants/rentPayments';
import { getOwnProfile } from '@/lib/hmore/services/tenants';
import { listAppointments } from '@/lib/hmore/services/timeline';
import { relativeTime } from '@/lib/maintenance';

const CLOSED = new Set(['completed', 'closed', 'cancelled']);

function rentValue(rows: RentObligation[] | null | undefined, fallback: string, nextDue: string): string {
  if (!rows || rows.length === 0) return fallback;
  const next = [...rows].sort((a, b) => {
    const ad = a.due_date ? new Date(a.due_date).getTime() : Number.POSITIVE_INFINITY;
    const bd = b.due_date ? new Date(b.due_date).getTime() : Number.POSITIVE_INFINITY;
    return ad - bd;
  })[0];
  if (!next) return fallback;
  const status = next.payment_status?.trim() ? titleCase(next.payment_status) : '';
  const due = shortDate(next.due_date);
  if (status && due) return `${status} · ${nextDue} ${due}`;
  if (status) return status;
  if (due) return `${nextDue} ${due}`;
  return fallback;
}

function whenLabel(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return relativeTime(date);
}

export function TenantHome() {
  const { user, hmore } = useAuth();
  const { prefs, fontScale, t } = useI18n();
  const net = useConnectivity();
  const profileQuery = useQuery({
    queryKey: ['hmore', 'tenant-me'],
    queryFn: getOwnProfile,
    enabled: !!hmore,
  });
  const housingQuery = useQuery({
    queryKey: ['hmore', 'tenant-housing'],
    queryFn: getOwnHousing,
    enabled: !!hmore,
  });
  const repairsQuery = useQuery({
    queryKey: ['hmore', 'maintenance'],
    queryFn: () => listMaintenance({ page: 1, page_size: 50 }),
  });
  const inboxQuery = useQuery({
    queryKey: ['hmore', 'inbox'],
    queryFn: () => orNull(() => listInbox()),
    enabled: !!hmore,
  });
  const rentQuery = useQuery({
    queryKey: ['hmore', 'rent-obligations'],
    queryFn: () => orNull(() => listMyRentObligations()),
    enabled: !!hmore,
  });
  const tenantId = profileQuery.data?.id;
  const appointmentsQuery = useQuery({
    queryKey: ['hmore', 'appointments', tenantId],
    queryFn: () => listAppointments(tenantId!),
    enabled: !!tenantId,
  });

  const offline = net.data === 'offline';
  if (
    ((profileQuery.isLoading && profileQuery.data === undefined) || (repairsQuery.isLoading && !repairsQuery.data)) &&
    !repairsQuery.data
  ) {
    if (offline && profileQuery.data === undefined) return <TenantOffline />;
    if (repairsQuery.isLoading && !repairsQuery.data) {
      if (offline) return <TenantOffline />;
      return <LoadingScreen message={t('housing.loading')} />;
    }
    if (profileQuery.isLoading && profileQuery.data === undefined) {
      return <LoadingScreen message={t('housing.loading')} />;
    }
  }
  if ((profileQuery.error || repairsQuery.error) && !repairsQuery.data) {
    if (offline) return <TenantOffline />;
    return (
      <TenantLoadError
        title={t('home.loadError')}
        onRetry={() => {
          profileQuery.refetch();
          repairsQuery.refetch();
          housingQuery.refetch();
        }}
      />
    );
  }

  const tenant = profileQuery.data;
  const housing = housingQuery.isError ? null : housingQuery.data;
  const repairs = repairsQuery.data?.items ?? [];
  const openRepairs = repairs.filter((row) => !CLOSED.has(row.status));
  const nextAppointment = (appointmentsQuery.data?.items ?? [])
    .filter((row) => row.status !== 'cancelled' && new Date(row.starts_at).getTime() >= Date.now())
    .sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime())[0];
  const recent = [...repairs]
    .sort(
      (a, b) =>
        new Date(b.updated_at || b.reported_at || b.created_at).getTime() -
        new Date(a.updated_at || a.reported_at || a.created_at).getTime(),
    )
    .slice(0, 3);
  const contrast = prefs.highContrast;
  const name = tenant?.preferred_name || user?.firstName || t('home.hello');
  const address = housing ? formatAssignedAddress(housing) : '';
  const room = housing?.room?.label;
  const place = [room, address].filter(Boolean).join(' · ');
  const heroSubtitle = place || tenant?.tenancy_reference || t('home.noRecord');
  const unread = inboxQuery.data ? inboxQuery.data.items.filter((item) => !item.read_at).length : null;
  const visitValue = nextAppointment ? shortWeekday(nextAppointment.starts_at) : t('home.none');

  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={
        <RefreshControl
          refreshing={
            profileQuery.isRefetching ||
            repairsQuery.isRefetching ||
            housingQuery.isRefetching ||
            inboxQuery.isRefetching ||
            rentQuery.isRefetching
          }
          onRefresh={() => {
            profileQuery.refetch();
            housingQuery.refetch();
            repairsQuery.refetch();
            inboxQuery.refetch();
            rentQuery.refetch();
            net.refetch();
            if (tenantId) appointmentsQuery.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <View style={styles.top}>
        <View style={styles.topCopy}>
          <Text style={[styles.kicker, contrast && styles.contrastText]}>{t('home.greeting')}</Text>
          <Text style={[styles.title, contrast && styles.contrastText, { fontSize: 32 * fontScale }]} numberOfLines={1}>
            {name}
          </Text>
        </View>
        <Avatar name={name} size={48} />
      </View>

      <HeroCard
        kicker={t('home.rentStatus')}
        value={rentValue(rentQuery.data, t('home.notRecorded'), t('home.nextDue'))}
        subtitle={heroSubtitle}
        ctaLabel={t('home.viewTenancy')}
        onCta={() => router.push('/(app)/(tabs)/tenancy')}
      />

      <StatTiles
        highContrast={contrast}
        items={[
          { value: String(openRepairs.length), label: t('home.openRepairs') },
          { value: unread == null ? t('home.none') : String(unread), label: t('home.newMessages') },
          { value: visitValue, label: t('home.nextVisit') },
        ]}
      />

      <Section title={t('communityHub.quickActions')}>
        <QuickActions
          actions={[
            {
              key: 'repair',
              label: t('home.reportRepair'),
              icon: 'construct-outline',
              tone: 'blue',
              onPress: () => router.push('/(app)/maintenance/new'),
            },
            {
              key: 'message',
              label: t('home.message'),
              icon: 'chatbubble-outline',
              tone: 'indigo',
              onPress: () => router.push('/(app)/notifications'),
            },
            {
              key: 'help',
              label: t('nav.helpNearMe'),
              icon: 'location-outline',
              tone: 'amber',
              onPress: () => router.push('/(app)/help-near-me'),
            },
            {
              key: 'daily',
              label: t('home.daily'),
              icon: 'heart-outline',
              tone: 'green',
              onPress: () => router.push(DAILY_HREF),
            },
          ]}
        />
      </Section>

      <Section title={t('home.recent')} actionLabel={t('home.seeAll')} onAction={() => router.push('/(app)/(tabs)/maintenance')}>
        {recent.length === 0 && !nextAppointment ? (
          <Text style={[styles.muted, contrast && styles.contrastMuted]}>{t('repairs.emptyBody')}</Text>
        ) : (
          <View>
            {nextAppointment ? (
              <ActivityRow
                highContrast={contrast}
                name={nextAppointment.title}
                title={nextAppointment.title}
                meta={[shortDate(nextAppointment.starts_at), shortTime(nextAppointment.starts_at), nextAppointment.location]
                  .filter(Boolean)
                  .join(' · ')}
                chip={titleCase(nextAppointment.status)}
                chipTone="indigo"
                onPress={() => router.push('/(app)/(tabs)/support')}
              />
            ) : null}
            {recent.map((row) => {
              const updated = whenLabel(row.updated_at || row.reported_at || row.created_at);
              return (
                <ActivityRow
                  key={row.id}
                  highContrast={contrast}
                  name={row.title}
                  title={row.title}
                  meta={updated ? `${t('home.repairLine')} · ${t('home.updated')} ${updated}` : row.reference_number}
                  chip={repairStatusText(row.status)}
                  chipTone={repairStatusTone(row.status)}
                  onPress={() => router.push(`/(app)/maintenance/${row.id}`)}
                />
              );
            })}
          </View>
        )}
      </Section>
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastMuted: { color: '#111111' },
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: theme.spacing.md },
  topCopy: { flex: 1, minWidth: 0 },
  kicker: { fontFamily: FONT_SEMIBOLD, color: theme.colors.textSecondary, fontSize: 14 },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.6, marginTop: 2 },
  muted: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 14, lineHeight: 20 },
});
