import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { compactGBP, InitialsTile, StatTiles, titleCase } from '@/components/dashboard/mobileChrome';
import { repairStatusText, repairStatusTone } from '@/components/maintenance/repairTone';
import { Card } from '@/components/ui/Card';
import { Chip, toneColors, type Tone } from '@/components/ui/Chip';
import { HeroCard } from '@/components/ui/HeroCard';
import { Avatar } from '@/components/ui/ListRow';
import { Screen } from '@/components/ui/Screen';
import { Section } from '@/components/ui/Section';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard, useProperties } from '@/hooks/useApi';
import { useI18n } from '@/hooks/useI18n';
import { NotificationItem, PropertyItem } from '@/lib/api';
import { HmoreApiError, hmoreErrorMessage } from '@/lib/hmore/client';
import { listDocuments } from '@/lib/hmore/services/documents';
import { getLandlordEnterpriseDashboard, type LandlordEnterpriseDashboard } from '@/lib/hmore/services/landlordDashboard';
import { listMaintenance } from '@/lib/hmore/services/maintenance';
import type { ManagedDocument, MaintenanceRequest } from '@/lib/hmore/types';
import { navigateFromNotification } from '@/lib/notificationNavigation';

const CLOSED = new Set(['completed', 'closed', 'cancelled']);

async function orNull<T>(task: () => Promise<T>): Promise<T | null> {
  try {
    return await task();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 400 || error.status === 403 || error.status === 404)) {
      return null;
    }
    throw error;
  }
}

function portfolioRent(properties: PropertyItem[]): { amount: number; occupiedRooms: number } {
  let amount = 0;
  let occupiedRooms = 0;
  for (const property of properties) {
    for (const room of property.rooms ?? []) {
      if (room.status !== 'occupied') continue;
      occupiedRooms += 1;
      amount += room.rentPcm || 0;
    }
  }
  return { amount, occupiedRooms };
}

function legacyOccupancy(properties: PropertyItem[]) {
  const occupied = properties.reduce(
    (sum, property) => sum + (property.rooms?.filter((room) => room.status === 'occupied').length ?? 0),
    0,
  );
  const rooms = properties.reduce((sum, property) => sum + (property.rooms?.length ?? 0), 0);
  const vacant = Math.max(rooms - occupied, 0);
  const listings = properties.reduce(
    (sum, property) => sum + (property.rooms?.filter((room) => room.listing).length ?? 0),
    0,
  );
  return { occupied, rooms, vacant, listings };
}

function certDue(doc: ManagedDocument): boolean {
  if (doc.expiry_tracking === 'expired' || doc.expiry_tracking === 'expiring_soon') return true;
  if (doc.expiry_tracking) return false;
  if (!doc.expiry_date) return false;
  const date = new Date(doc.expiry_date);
  return !Number.isNaN(date.getTime()) && date.getTime() < Date.now();
}

function daysUntil(iso?: string | null): number | null {
  if (!iso) return null;
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return null;
  return Math.ceil((time - Date.now()) / (24 * 60 * 60 * 1000));
}

function certChip(doc: ManagedDocument): { label: string; tone: Tone } {
  const days = daysUntil(doc.expiry_date);
  if (doc.expiry_tracking === 'expired' || (days != null && days < 0)) return { label: 'Expired', tone: 'red' };
  if (days != null && days >= 0) return { label: days === 1 ? '1 day' : `${days} days`, tone: 'amber' };
  return { label: 'Due soon', tone: 'amber' };
}

function knownListingCount(properties: PropertyItem[]): number | null {
  if (!properties.some((property) => Array.isArray(property.rooms) && property.rooms.length > 0)) return null;
  return properties.reduce((sum, property) => sum + (property.rooms?.filter((room) => room.listing).length ?? 0), 0);
}

function vacancyLine(vacant: number, listings: number | null): string {
  const rooms = `${vacant} room${vacant === 1 ? '' : 's'} vacant`;
  if (!listings) return rooms;
  return `${rooms} · ${listings} listing${listings === 1 ? '' : 's'} live`;
}

export function LandlordHome() {
  const { user, hmore } = useAuth();
  const { prefs, fontScale, t } = useI18n();
  const dashboard = useDashboard();
  const propertiesQuery = useProperties();
  const maintenanceQuery = useQuery({
    queryKey: ['hmore', 'maintenance', 'landlord-home'],
    queryFn: () => orNull(() => listMaintenance({ page: 1, page_size: 50 })),
    enabled: !!hmore,
  });
  const documentsQuery = useQuery({
    queryKey: ['hmore', 'documents', 'landlord-home'],
    queryFn: () => orNull(() => listDocuments()),
    enabled: !!hmore,
  });
  const enterpriseQuery = useQuery({
    queryKey: ['hmore', 'landlord-dashboard'],
    queryFn: () => orNull(() => getLandlordEnterpriseDashboard()),
    enabled: !!hmore,
  });

  const loading =
    propertiesQuery.isLoading ||
    (!hmore && dashboard.isLoading) ||
    (!!hmore && (maintenanceQuery.isLoading || documentsQuery.isLoading || enterpriseQuery.isLoading));
  const error = propertiesQuery.error ?? (!hmore ? dashboard.error : null);
  if (loading) return <LoadingScreen message="Loading..." />;
  if (error || (!hmore && !dashboard.data)) {
    return (
      <ErrorState
        message={hmoreErrorMessage(error, 'Could not load your home screen.')}
        onRetry={() => {
          propertiesQuery.refetch();
          dashboard.refetch();
        }}
      />
    );
  }

  const contrast = prefs.highContrast;
  const name = user?.firstName?.trim() || 'there';
  const fullName = `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim() || name;
  const properties = propertiesQuery.data?.properties ?? [];
  const dash: LandlordEnterpriseDashboard | null = enterpriseQuery.data ?? null;
  const repairs = (maintenanceQuery.data?.items ?? []).filter((row) => !CLOSED.has(row.status));
  const certs = (documentsQuery.data?.items ?? []).filter(certDue);

  const liveListings = hmore ? null : knownListingCount(properties);
  const hero = hmore ? hmoreHero(dash, properties.length, liveListings) : legacyHero(properties, liveListings);
  const openRepairs = hmore
    ? maintenanceQuery.data
      ? String(repairs.length)
      : dash
        ? String(dash.repairs.open)
        : '—'
    : dashboard.data?.stats.openMaintenance != null
      ? String(dashboard.data.stats.openMaintenance)
      : '—';
  const certsDue = hmore
    ? documentsQuery.data
      ? String(certs.length)
      : '—'
    : dashboard.data?.stats.expiringDocs != null
      ? String(dashboard.data.stats.expiringDocs)
      : '—';
  const rentTile = hmore ? hmoreRent(dash) : legacyRent(properties);

  const activity = hmore ? hmoreActivity(repairs, certs) : legacyActivity(dashboard.data?.notifications ?? []);

  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={
        <RefreshControl
          refreshing={
            propertiesQuery.isRefetching ||
            dashboard.isRefetching ||
            maintenanceQuery.isRefetching ||
            documentsQuery.isRefetching ||
            enterpriseQuery.isRefetching
          }
          onRefresh={() => {
            propertiesQuery.refetch();
            dashboard.refetch();
            if (hmore) {
              maintenanceQuery.refetch();
              documentsQuery.refetch();
              enterpriseQuery.refetch();
            }
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <View style={styles.top}>
        <View style={styles.topCopy}>
          <Text style={[styles.kicker, contrast && styles.contrastText]}>Portfolio overview</Text>
          <Text style={[styles.title, contrast && styles.contrastText, { fontSize: 32 * fontScale }]} numberOfLines={1}>
            {name}
          </Text>
        </View>
        <Avatar name={fullName} size={48} />
      </View>

      <HeroCard
        kicker="Occupancy"
        value={hero.value}
        title={hero.title}
        subtitle={hero.subtitle}
        ctaLabel={hero.cta}
        onCta={() => router.push(hero.href)}
      />

      <StatTiles
        highContrast={contrast}
        items={[
          { value: openRepairs, label: t('home.openRepairs') },
          { value: certsDue, label: 'Certs due' },
          rentTile,
        ]}
      />

      <Section title={t('communityHub.quickActions')}>
        <View style={styles.actions}>
          {[
            { key: 'add', letters: 'AP', label: 'Add property', tone: 'blue' as Tone, onPress: () => router.push('/(app)/property/new') },
            { key: 'repair', letters: 'LR', label: 'Log repair', tone: 'indigo' as Tone, onPress: () => router.push('/(app)/maintenance/new') },
            { key: 'inspect', letters: 'IN', label: 'Inspection', tone: 'amber' as Tone, onPress: () => router.push('/(app)/(tabs)/inspections') },
            { key: 'listing', letters: 'LI', label: 'Listing', tone: 'green' as Tone, onPress: () => router.push('/(app)/(tabs)/listings') },
          ].map((action) => {
            const colors = toneColors[action.tone];
            return (
              <Pressable
                key={action.key}
                onPress={action.onPress}
                accessibilityRole="button"
                accessibilityLabel={action.label}
                style={({ pressed }) => [styles.action, pressed && styles.actionPressed]}
              >
                <View style={[styles.letter, { backgroundColor: colors.bg }]}>
                  <Text style={[styles.letterText, { color: colors.text }]}>{action.letters}</Text>
                </View>
                <Text style={[styles.actionLabel, contrast && styles.contrastText]} numberOfLines={2}>
                  {action.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </Section>

      <Section title="Needs attention" actionLabel={t('home.seeAll')} onAction={() => router.push('/(app)/notifications')}>
        {activity.length === 0 ? (
          <Text style={[styles.muted, contrast && styles.contrastMuted]}>Open repairs and certificates that need attention show up here.</Text>
        ) : (
          <View style={styles.list}>
            {activity.map((row) => (
              <Card key={row.key} style={contrast ? styles.contrastCard : undefined} onPress={row.onPress}>
                <View style={styles.row}>
                  <InitialsTile name={row.name} size={40} />
                  <View style={styles.copy}>
                    <Text style={styles.rowTitle} numberOfLines={1}>{row.title}</Text>
                    <Text style={styles.rowMeta} numberOfLines={1}>{row.meta}</Text>
                  </View>
                  <Chip label={row.chip} tone={row.tone} />
                </View>
              </Card>
            ))}
          </View>
        )}
      </Section>
    </Screen>
  );
}

function hmoreHero(dash: LandlordEnterpriseDashboard | null, propertyCount: number, listings: number | null): {
  value?: string;
  title?: string;
  subtitle?: string;
  cta: string;
  href: '/(app)/property/new' | '/(app)/(tabs)/properties';
} {
  if (dash && dash.total_rooms > 0) {
    const percent = Math.round((dash.occupied_rooms / dash.total_rooms) * 100);
    const vacant = dash.vacant_rooms;
    return {
      value: `${percent}% · ${dash.occupied_rooms} of ${dash.total_rooms} rooms`,
      subtitle: vacancyLine(vacant, listings),
      cta: vacant > 0 ? 'View vacancies' : 'View properties',
      href: '/(app)/(tabs)/properties',
    };
  }
  const count = dash?.total_properties ?? propertyCount;
  if (count === 0) {
    return {
      title: 'Add your first property',
      subtitle: 'Rooms, certificates and repairs show up here once a property is added.',
      cta: 'Add property',
      href: '/(app)/property/new',
    };
  }
  return {
    value: `${count} propert${count === 1 ? 'y' : 'ies'}`,
    cta: 'View properties',
    href: '/(app)/(tabs)/properties',
  };
}

function legacyHero(properties: PropertyItem[], listings: number | null): {
  value?: string;
  title?: string;
  subtitle?: string;
  cta: string;
  href: '/(app)/property/new' | '/(app)/(tabs)/properties';
} {
  if (properties.length === 0) {
    return {
      title: 'Add your first property',
      subtitle: 'Rooms, certificates and repairs show up here once a property is added.',
      cta: 'Add property',
      href: '/(app)/property/new',
    };
  }
  const { occupied, rooms, vacant } = legacyOccupancy(properties);
  if (rooms === 0) {
    return {
      value: `${properties.length} propert${properties.length === 1 ? 'y' : 'ies'}`,
      cta: 'View properties',
      href: '/(app)/(tabs)/properties',
    };
  }
  const percent = Math.round((occupied / rooms) * 100);
  return {
    value: `${percent}% · ${occupied} of ${rooms} rooms`,
    subtitle: vacancyLine(vacant, listings),
    cta: vacant > 0 ? 'View vacancies' : 'View properties',
    href: '/(app)/(tabs)/properties',
  };
}

function hmoreRent(dash: LandlordEnterpriseDashboard | null): { value: string; label: string } {
  if (!dash) return { value: '—', label: 'Rent due' };
  return { value: String(dash.rent.due), label: 'Rent due' };
}

function legacyRent(properties: PropertyItem[]): { value: string; label: string } {
  const { amount, occupiedRooms } = portfolioRent(properties);
  if (occupiedRooms === 0) return { value: '—', label: 'Rent this month' };
  return { value: compactGBP(amount), label: 'Rent this month' };
}

type ActivityRow = {
  key: string;
  name: string;
  title: string;
  meta: string;
  chip: string;
  tone: Tone;
  onPress: () => void;
};

function hmoreActivity(repairs: MaintenanceRequest[], certs: ManagedDocument[]): ActivityRow[] {
  const repairRows: ActivityRow[] = [...repairs]
    .sort((a, b) => new Date(b.updated_at || b.reported_at).getTime() - new Date(a.updated_at || a.reported_at).getTime())
    .slice(0, 3)
    .map((row) => ({
      key: row.id,
      name: row.title,
      title: row.title,
      meta: `${row.reference_number} · ${formatUKDate(row.reported_at || row.created_at)}`,
      chip: repairStatusText(row.status),
      tone: repairStatusTone(row.status),
      onPress: () => router.push(`/(app)/maintenance/${row.id}`),
    }));
  const certRows: ActivityRow[] = certs.slice(0, 4 - repairRows.length).map((doc) => {
    const chip = certChip(doc);
    return {
      key: doc.id,
      name: doc.title,
      title: doc.title,
      meta: doc.expiry_date ? formatUKDate(doc.expiry_date) : doc.reference_number || 'Certificate',
      chip: chip.label,
      tone: chip.tone,
      onPress: () => router.push('/(app)/(tabs)/compliance'),
    };
  });
  return [...repairRows, ...certRows];
}

function legacyActivity(notifications: NotificationItem[]): ActivityRow[] {
  return notifications.slice(0, 4).map((item) => ({
    key: item.id,
    name: item.title,
    title: item.title,
    meta: `${item.body} · ${formatUKDate(item.createdAt)}`,
    chip: item.read ? titleCase(item.type || 'update') : 'New',
    tone: item.read ? 'gray' : 'blue',
    onPress: () => navigateFromNotification(item),
  }));
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastMuted: { color: '#111111' },
  contrastCard: { borderWidth: 2, borderColor: '#000000' },
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: theme.spacing.md },
  topCopy: { flex: 1, minWidth: 0 },
  kicker: { fontFamily: FONT_SEMIBOLD, color: theme.colors.textSecondary, fontSize: 14 },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.6, marginTop: 2 },
  muted: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 14, lineHeight: 20 },
  actions: { flexDirection: 'row', justifyContent: 'space-between', gap: theme.spacing.sm, marginBottom: theme.spacing.sm },
  action: { flex: 1, alignItems: 'center', minHeight: 44, paddingVertical: 4 },
  actionPressed: { opacity: 0.8 },
  letter: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  letterText: { fontFamily: FONT_BOLD, fontWeight: '700', fontSize: 14 },
  actionLabel: { fontSize: 12, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text, textAlign: 'center' },
  list: { gap: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  rowTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  rowMeta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary, marginTop: 2 },
});
