import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { FilterChips, InitialsTile, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useProperties } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import { PropertyItem } from '@/lib/api';
import { assessPropertyCompliance } from '@/lib/compliance';

type PropertyFilter = 'all' | 'full' | 'vacant' | 'action';

const FILTERS: { id: PropertyFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'full', label: 'Fully let' },
  { id: 'vacant', label: 'Vacancies' },
  { id: 'action', label: 'Action' },
];

function daysUntil(iso?: string | null): number | null {
  if (!iso) return null;
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return null;
  return Math.ceil((time - Date.now()) / (24 * 60 * 60 * 1000));
}

function certSignal(property: PropertyItem): { label: string; tone: Tone } | null {
  const docs = property.documents;
  if (!docs?.length) return null;
  let gasExpired = false;
  let gasDue = false;
  let otherDue = false;
  for (const doc of docs) {
    const days = doc.daysLeft ?? daysUntil(doc.expiryDate);
    if (days == null || days > 30) continue;
    const blob = `${doc.type} ${doc.name}`.toLowerCase();
    if (/gas/.test(blob)) {
      if (days < 0) gasExpired = true;
      else gasDue = true;
    } else if (days <= 30) {
      otherDue = true;
    }
  }
  if (gasExpired) return { label: 'Gas due', tone: 'red' };
  if (gasDue) return { label: 'Gas due', tone: 'amber' };
  if (otherDue) return { label: 'Cert due', tone: 'amber' };
  return null;
}

function propertyChip(total: number, voids: number, repairs: number, score: number, cert: { label: string; tone: Tone } | null): { label: string; tone: Tone } {
  if (cert) return cert;
  if (total === 0 && repairs === 0 && score >= 85) return { label: 'No rooms', tone: 'gray' };
  if (repairs > 0 && score < 60) return { label: 'Action', tone: 'red' };
  if (voids > 0) return { label: voids === 1 ? '1 vacant' : `${voids} vacant`, tone: 'blue' };
  if (repairs > 0) return { label: repairs === 1 ? '1 repair' : `${repairs} repairs`, tone: 'amber' };
  if (score < 85) return { label: 'Action', tone: 'amber' };
  return { label: 'Full', tone: 'green' };
}

export default function PropertiesScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(TAB_ROLES.properties);
  if (guard) return guard;

  const { user, hmore } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useProperties();
  const canAdd = ['landlord', 'admin'].includes(user?.role ?? '');
  const [filter, setFilter] = useState<PropertyFilter>('all');
  const [query, setQuery] = useState('');

  const properties = data?.properties ?? [];
  const occupancyKnown = !hmore;
  const rooms = properties.reduce((sum, property) => sum + (property.rooms?.length ?? 0), 0);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return properties.filter((property) => {
      const occupied = property.rooms?.filter((room) => room.status === 'occupied').length ?? 0;
      const total = property.rooms?.length ?? 0;
      const voids = total - occupied;
      const score = assessPropertyCompliance(property).score;
      const repairs = property._count?.maintenance ?? 0;
      const cert = certSignal(property);
      if (!occupancyKnown) {
        if (!needle) return true;
        const haystack = `${property.name} ${property.addressLine1} ${property.postcode} ${property.city}`.toLowerCase();
        return haystack.includes(needle);
      }
      if (filter === 'full' && !(total > 0 && voids === 0)) return false;
      if (filter === 'vacant' && voids <= 0) return false;
      if (filter === 'action' && !(score < 85 || repairs > 0 || cert)) return false;
      if (!needle) return true;
      const haystack = `${property.name} ${property.addressLine1} ${property.postcode} ${property.city}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [properties, filter, query, occupancyKnown]);

  if (isLoading) return <LoadingScreen message="Loading properties..." />;
  if (error) return <ErrorState message="Could not load properties" onRetry={refetch} />;

  return (
    <ListScreen
      data={filtered}
      keyExtractor={(item) => item.id}
      refreshing={isRefetching}
      onRefresh={refetch}
      contentContainerStyle={filtered.length === 0 ? styles.emptyList : undefined}
      ListHeaderComponent={
        <View>
          <ScreenHeader
            title="Properties"
            subtitle={
              occupancyKnown
                ? `${properties.length} propert${properties.length === 1 ? 'y' : 'ies'} · ${rooms} rooms`
                : `${properties.length} propert${properties.length === 1 ? 'y' : 'ies'}`
            }
            action={
              canAdd ? (
                <Button title="Add" icon="add" size="sm" onPress={() => router.push('/(app)/property/new')} />
              ) : undefined
            }
          />
          <SearchField value={query} onChangeText={setQuery} placeholder="Search address or postcode" />
          {occupancyKnown && properties.length > 0 ? (
            <FilterChips options={FILTERS} value={filter} onChange={(id) => setFilter(id as PropertyFilter)} />
          ) : null}
        </View>
      }
      ListEmptyComponent={
        <EmptyState
          title={properties.length === 0 ? 'No properties yet' : 'Nothing in this filter'}
          message={
            properties.length === 0
              ? 'Add a property to manage rooms, certificates and repairs.'
              : 'Try another filter or search.'
          }
          icon="business-outline"
          actionLabel={canAdd && properties.length === 0 ? 'Add property' : undefined}
          onAction={canAdd && properties.length === 0 ? () => router.push('/(app)/property/new') : undefined}
        />
      }
      renderItem={({ item }) => <PropertyRow property={item} occupancyKnown={occupancyKnown} />}
    />
  );
}

function PropertyRow({ property, occupancyKnown }: { property: PropertyItem; occupancyKnown: boolean }) {
  const occupied = property.rooms?.filter((room) => room.status === 'occupied').length ?? 0;
  const total = property.rooms?.length ?? 0;
  const voids = total - occupied;
  const repairs = property._count?.maintenance ?? 0;
  const score = assessPropertyCompliance(property).score;
  const cert = certSignal(property);
  const chip = occupancyKnown ? propertyChip(total, voids, repairs, score, cert) : cert;
  const title = property.addressLine1 || property.name;
  const licence = property.hmoLicenceNumber ? 'Licence held' : null;
  const meta = [occupancyKnown ? `${total} rooms` : null, property.postcode, licence].filter(Boolean).join(' · ');

  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/property/${property.id}`)}>
      <View style={styles.row}>
        <InitialsTile name={title} size={42} />
        <View style={styles.copy}>
          <Text style={styles.title} numberOfLines={1}>{title}</Text>
          <Text style={styles.meta} numberOfLines={1}>{meta}</Text>
        </View>
        {chip ? <Chip label={chip.label} tone={chip.tone} /> : null}
        <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  emptyList: { flexGrow: 1 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  meta: { fontSize: 13, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 },
});
