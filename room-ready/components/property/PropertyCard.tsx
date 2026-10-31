import { router } from 'expo-router';
import { Image, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { PropertyItem } from '@/lib/api';
import { assessPropertyCompliance } from '@/lib/compliance';
import { propertyCoverUrl } from '@/lib/propertyCovers';

export function PropertyCard({ property }: { property: PropertyItem }) {
  const occupied = property.rooms?.filter((r) => r.status === 'occupied').length ?? 0;
  const total = property.rooms?.length ?? 0;
  const voids = total - occupied;
  const openRepairs = property._count?.maintenance ?? 0;
  const rents = property.rooms?.map((r) => r.rentPcm) ?? [];
  const minRent = rents.length > 0 ? Math.min(...rents) : 0;
  const compliance = assessPropertyCompliance(property);
  const scoreTone =
    compliance.score >= 85 ? 'success' : compliance.score >= 60 ? 'warning' : 'error';
  const cover = propertyCoverUrl(property.id);

  return (
    <Card
      style={styles.card}
      padded={false}
      onPress={() => router.push(`/(app)/property/${property.id}`)}
    >
      <Image source={{ uri: cover }} style={styles.cover} resizeMode="cover" />
      <View style={styles.body}>
        <View style={styles.top}>
          <View style={styles.copy}>
            <Text style={styles.name} numberOfLines={1}>{property.name}</Text>
            <Text style={styles.address} numberOfLines={1}>
              {property.addressLine1}, {property.postcode}
            </Text>
          </View>
          <Badge label={`${compliance.score}%`} variant={scoreTone} format={false} />
        </View>

        <View style={styles.stats}>
          <View style={styles.stat}>
            <Text style={styles.statValue}>{occupied}/{total}</Text>
            <Text style={styles.statLabel}>Occupied</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={styles.statValue}>{voids}</Text>
            <Text style={styles.statLabel}>Voids</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={styles.statValue}>{minRent > 0 ? formatGBP(minRent) : '—'}</Text>
            <Text style={styles.statLabel}>From</Text>
          </View>
        </View>

        <View style={styles.footer}>
          <View style={styles.footerLeft}>
            {property.hmoLicenceNumber ? (
              <>
                <Ionicons name="shield-checkmark-outline" size={13} color={theme.colors.secondary} />
                <Text style={styles.licence} numberOfLines={1}>{property.hmoLicenceNumber}</Text>
              </>
            ) : (
              <Text style={styles.city}>{property.city}</Text>
            )}
          </View>
          {openRepairs > 0 ? (
            <Badge label={`${openRepairs} repair${openRepairs === 1 ? '' : 's'}`} variant="warning" format={false} />
          ) : (
            <View style={styles.openRow}>
              <Text style={styles.open}>Open</Text>
              <Ionicons name="chevron-forward" size={14} color={theme.colors.secondary} />
            </View>
          )}
        </View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.sm, overflow: 'hidden' },
  cover: { width: '100%', height: 120, backgroundColor: theme.colors.surfaceMuted },
  body: { padding: theme.spacing.md },
  top: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  copy: { flex: 1, minWidth: 0 },
  name: {
    fontSize: 16,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.2,
  },
  address: {
    color: theme.colors.textSecondary,
    marginTop: 3,
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
  },
  stats: {
    flexDirection: 'row',
    marginTop: theme.spacing.md,
    paddingTop: theme.spacing.md,
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderLight,
  },
  stat: { flex: 1, alignItems: 'center' },
  statDivider: { width: 1, backgroundColor: theme.colors.borderLight },
  statValue: {
    fontSize: 14,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
  },
  statLabel: {
    fontSize: 11,
    color: theme.colors.textMuted,
    marginTop: 2,
    fontFamily: FONT_MEDIUM,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: theme.spacing.md,
    gap: 8,
  },
  footerLeft: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 5, minWidth: 0 },
  licence: {
    color: theme.colors.secondary,
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    flexShrink: 1,
  },
  city: { color: theme.colors.textMuted, fontSize: 12, fontFamily: FONT_MEDIUM },
  openRow: { flexDirection: 'row', alignItems: 'center', gap: 2 },
  open: { color: theme.colors.secondary, fontSize: 13, fontFamily: FONT_SEMIBOLD, fontWeight: '600' },
});
