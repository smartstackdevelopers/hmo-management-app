import { router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { InitialsTile } from '@/components/dashboard/mobileChrome';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { PropertyItem } from '@/lib/api';
import { assessPropertyCompliance } from '@/lib/compliance';

export function PropertyCard({ property }: { property: PropertyItem }) {
  const occupied = property.rooms?.filter((room) => room.status === 'occupied').length ?? 0;
  const total = property.rooms?.length ?? 0;
  const voids = total - occupied;
  const repairs = property._count?.maintenance ?? 0;
  const score = assessPropertyCompliance(property).score;
  const chip = propertyChip(voids, repairs, score);
  const licence = property.hmoLicenceNumber ? 'Licence OK' : null;

  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/property/${property.id}`)}>
      <View style={styles.row}>
        <InitialsTile name={property.addressLine1 || property.name} size={42} />
        <View style={styles.copy}>
          <Text style={styles.title} numberOfLines={1}>{property.addressLine1 || property.name}</Text>
          <Text style={styles.meta} numberOfLines={1}>
            {[`${total} rooms`, property.postcode, licence].filter(Boolean).join(' · ')}
          </Text>
        </View>
        <Chip label={chip.label} tone={chip.tone} />
      </View>
    </Card>
  );
}

function propertyChip(voids: number, repairs: number, score: number): { label: string; tone: Tone } {
  if (repairs > 0 && score < 60) return { label: 'Action', tone: 'red' };
  if (voids > 0) return { label: voids === 1 ? '1 vacant' : `${voids} vacant`, tone: 'blue' };
  if (repairs > 0) return { label: repairs === 1 ? '1 repair' : `${repairs} repairs`, tone: 'amber' };
  if (score < 85) return { label: 'Action', tone: 'amber' };
  return { label: 'Full', tone: 'green' };
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  meta: { fontSize: 13, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 },
});
