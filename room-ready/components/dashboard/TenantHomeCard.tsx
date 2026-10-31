import { router } from 'expo-router';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { propertyCoverUrl } from '@/lib/propertyCovers';
import { TenancyItem } from '@/lib/api';

export function TenantHomeCard({ tenancy }: { tenancy: TenancyItem }) {
  const property = tenancy.room?.property;
  if (!property) return null;

  const cover = propertyCoverUrl(property.id);

  return (
    <Card style={styles.card} padded={false} onPress={() => router.push('/(app)/(tabs)/tenancy')}>
      <Image source={{ uri: cover }} style={styles.cover} resizeMode="cover" />
      <View style={styles.body}>
        <View style={styles.top}>
          <View style={styles.copy}>
            <Text style={styles.eyebrow}>Your home</Text>
            <Text style={styles.title} numberOfLines={1}>{property.name}</Text>
            <Text style={styles.address} numberOfLines={2}>
              {property.addressLine1}, {property.city} {property.postcode}
            </Text>
          </View>
          <Badge label="Active" variant="success" />
        </View>

        <View style={styles.metaRow}>
          <View style={styles.meta}>
            <Text style={styles.metaLabel}>Your room</Text>
            <Text style={styles.metaValue}>{tenancy.room?.name ?? 'Room'}</Text>
          </View>
          <View style={styles.meta}>
            <Text style={styles.metaLabel}>Rent</Text>
            <Text style={styles.metaValue}>{formatGBP(tenancy.rentPcm)}/pcm</Text>
          </View>
          <View style={styles.meta}>
            <Text style={styles.metaLabel}>Council tax</Text>
            <Text style={styles.metaValue}>Landlord</Text>
          </View>
        </View>

        <Pressable style={styles.linkRow} onPress={() => router.push('/(app)/(tabs)/tenancy')}>
          <Text style={styles.link}>View tenancy details</Text>
          <Ionicons name="chevron-forward" size={16} color={theme.colors.secondary} />
        </Pressable>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.lg, overflow: 'hidden' },
  cover: { width: '100%', height: 140, backgroundColor: theme.colors.surfaceMuted },
  body: { padding: theme.spacing.md },
  top: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  copy: { flex: 1, minWidth: 0 },
  eyebrow: {
    fontSize: 11,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.secondary,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 4,
  },
  title: {
    fontSize: 18,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.3,
  },
  address: {
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 4,
    lineHeight: 18,
  },
  metaRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: theme.spacing.md,
    paddingTop: theme.spacing.md,
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderLight,
  },
  meta: { flex: 1 },
  metaLabel: { fontSize: 11, color: theme.colors.textMuted, fontFamily: FONT_MEDIUM },
  metaValue: {
    fontSize: 13,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    marginTop: 2,
  },
  linkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: theme.spacing.md,
  },
  link: { fontSize: 14, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.secondary },
});
