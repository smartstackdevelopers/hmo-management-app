import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { FactGrid, HouseBanner, InitialsTile, titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useInspections, useProperty } from '@/hooks/useApi';
import { HmoreApiError } from '@/lib/hmore/client';
import { listMaintenance } from '@/lib/hmore/services/maintenance';

const CLOSED_REPAIRS = new Set(['completed', 'closed', 'cancelled']);

function roomTone(status: string): Tone {
  if (status === 'available') return 'green';
  if (status === 'occupied') return 'blue';
  return 'gray';
}

export default function PropertyDetailScreen() {
  useHideTabHeader();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user, hmore } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useProperty(id);
  const inspections = useInspections();
  const repairsQuery = useQuery({
    queryKey: ['hmore', 'maintenance', 'property', id],
    enabled: !!hmore && !!id,
    queryFn: async () => {
      try {
        return await listMaintenance({ page: 1, page_size: 50 });
      } catch (repairError) {
        if (repairError instanceof HmoreApiError && (repairError.status === 400 || repairError.status === 403 || repairError.status === 404)) {
          return null;
        }
        throw repairError;
      }
    },
  });

  if (isLoading) return <LoadingScreen message="Loading property..." />;
  if (error || !data) return <ErrorState message="Property not found" onRetry={refetch} />;

  const property = data.property;
  const rooms = property.rooms ?? [];
  const roomsKnown = rooms.length > 0 || !hmore;
  const occupied = rooms.filter((room) => room.status === 'occupied').length;
  const voids = Math.max(rooms.length - occupied, 0);
  const canManage = ['landlord', 'property_manager', 'admin'].includes(user?.role ?? '');
  const title = property.addressLine1 || property.name;
  const subtitle = [property.postcode, roomsKnown ? `${rooms.length} rooms` : null, property.hmoLicenceNumber ? 'HMO' : null]
    .filter(Boolean)
    .join(' · ');

  const monthly = rooms.reduce((sum, room) => sum + (room.status === 'occupied' ? room.rentPcm || 0 : 0), 0);
  const openRepairs = hmore
    ? repairsQuery.data
      ? repairsQuery.data.items.filter((row) => row.property_id === id && !CLOSED_REPAIRS.has(row.status)).length
      : null
    : property._count?.maintenance ?? 0;
  const propertyInspections = (inspections.data?.inspections ?? []).filter((item) => item.property?.id === property.id);
  const nextInspection = propertyInspections
    .filter((item) => new Date(item.scheduledAt).getTime() >= Date.now())
    .sort((a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime())[0];
  const timeline = propertyInspections
    .filter((item) => !Number.isNaN(new Date(item.completedAt || item.scheduledAt).getTime()))
    .sort((a, b) => new Date(b.completedAt || b.scheduledAt).getTime() - new Date(a.completedAt || a.scheduledAt).getTime());

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

      <HouseBanner />
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      <View style={styles.chips}>
        {roomsKnown && voids > 0 ? <Chip label={voids === 1 ? '1 vacancy' : `${voids} vacancies`} tone="blue" /> : null}
        {roomsKnown && rooms.length > 0 && voids === 0 ? <Chip label="Fully let" tone="green" /> : null}
        {property.hmoLicenceNumber ? <Chip label="Licence held" tone="indigo" /> : null}
      </View>

      <FactGrid
        items={[
          { label: 'Rooms', value: roomsKnown ? `${rooms.length} (${occupied} let)` : '—' },
          { label: 'Monthly rent', value: roomsKnown ? formatGBP(monthly) : '—' },
          { label: 'Open repairs', value: openRepairs == null ? '—' : String(openRepairs) },
          { label: 'Next inspection', value: nextInspection ? formatUKDate(nextInspection.scheduledAt) : '—' },
        ]}
      />

          {roomsKnown && rooms.length > 0 ? (
        <View style={styles.list}>
          {rooms.map((room) => {
            const meta = [formatGBP(room.rentPcm), room.sizeSqm ? `${room.sizeSqm} m²` : null].filter(Boolean).join(' · ');
            const onPress = room.listing?.id
              ? () => router.push(`/(app)/listing/${room.listing!.id}`)
              : canManage && room.status === 'available'
                ? () => router.push({ pathname: '/(app)/listing/new', params: { roomId: room.id, propertyId: id } })
                : undefined;
            return (
              <Card key={room.id} style={styles.card} onPress={onPress}>
                <View style={styles.row}>
                  <InitialsTile name={room.name} size={40} />
                  <View style={styles.copy}>
                    <Text style={styles.rowTitle} numberOfLines={1}>{room.name}</Text>
                    <Text style={styles.rowMeta} numberOfLines={1}>{meta}</Text>
                  </View>
                  <Chip label={titleCase(room.status)} tone={roomTone(room.status)} />
                  {onPress ? <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} /> : null}
                </View>
              </Card>
            );
          })}
        </View>
      ) : null}

      {timeline.length > 0 ? (
        <View style={styles.timeline}>
          <Text style={styles.section}>Timeline</Text>
          {timeline.map((item) => (
            <View key={item.id} style={styles.event}>
              <View style={styles.dot} />
              <Text style={styles.eventTitle} numberOfLines={1}>{titleCase(item.status)}</Text>
              <Text style={styles.eventDate}>{formatUKDate(item.completedAt || item.scheduledAt)}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {canManage ? (
        <Button
          title="Manage rooms"
          onPress={() => router.push({ pathname: '/(app)/property/add-room', params: { propertyId: id } })}
          fullWidth
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
  title: { fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4 },
  subtitle: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 6, fontSize: 14 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  list: { gap: theme.spacing.sm, marginBottom: theme.spacing.md },
  card: {},
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  rowTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  rowMeta: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary, marginTop: 2 },
  timeline: { marginBottom: theme.spacing.lg },
  section: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text, marginBottom: theme.spacing.sm },
  event: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 8 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: theme.colors.secondary },
  eventTitle: { flex: 1, fontFamily: FONT_MEDIUM, color: theme.colors.text, fontSize: 14 },
  eventDate: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, fontSize: 12 },
});
