import { router } from 'expo-router';
import { Image, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { PropertyItem } from '@/lib/api';
import { assessPropertyCompliance } from '@/lib/compliance';
import { propertyCoverUrl } from '@/lib/propertyCovers';

interface PortfolioHomeCardProps {
  properties: PropertyItem[];
  portfolioScore: number | null;
  openRepairs: number;
  expiringDocs: number;
}

export function PortfolioHomeCard({
  properties,
  portfolioScore,
  openRepairs,
  expiringDocs,
}: PortfolioHomeCardProps) {
  if (properties.length === 0) {
    return (
      <Card style={styles.empty} onPress={() => router.push('/(app)/property/new')}>
        <View style={styles.emptyIcon}>
          <Ionicons name="business-outline" size={22} color={theme.colors.secondary} />
        </View>
        <Text style={styles.emptyTitle}>Start your portfolio</Text>
        <Text style={styles.emptyBody}>Add your first HMO to manage rooms, certificates and repairs.</Text>
        <Text style={styles.link}>Add property →</Text>
      </Card>
    );
  }

  const featured = properties[0];
  const occupied = properties.reduce(
    (sum, p) => sum + (p.rooms?.filter((r) => r.status === 'occupied').length ?? 0),
    0
  );
  const rooms = properties.reduce((sum, p) => sum + (p.rooms?.length ?? 0), 0);
  const cover = propertyCoverUrl(featured.id);
  const score = portfolioScore ?? assessPropertyCompliance(featured).score;
  const scoreTone = score >= 85 ? 'success' : score >= 60 ? 'warning' : 'error';

  return (
    <Card style={styles.card} padded={false} onPress={() => router.push('/(app)/(tabs)/properties')}>
      <Image source={{ uri: cover }} style={styles.cover} resizeMode="cover" />
      <View style={styles.body}>
        <View style={styles.top}>
          <View style={styles.copy}>
            <Text style={styles.eyebrow}>Your portfolio</Text>
            <Text style={styles.title} numberOfLines={1}>
              {properties.length} HMO{properties.length === 1 ? '' : 's'} · {rooms} rooms
            </Text>
            <Text style={styles.address} numberOfLines={1}>
              Featured · {featured.name}
            </Text>
          </View>
          <Badge label={`${score}% checks`} variant={scoreTone} format={false} />
        </View>

        <View style={styles.metaRow}>
          <View style={styles.meta}>
            <Text style={styles.metaLabel}>Occupied</Text>
            <Text style={styles.metaValue}>
              {occupied}/{rooms}
            </Text>
          </View>
          <View style={styles.meta}>
            <Text style={styles.metaLabel}>Open repairs</Text>
            <Text style={styles.metaValue}>{openRepairs}</Text>
          </View>
          <View style={styles.meta}>
            <Text style={styles.metaLabel}>Docs due</Text>
            <Text style={styles.metaValue}>{expiringDocs}</Text>
          </View>
        </View>

        <View style={styles.linkRow}>
          <Text style={styles.link}>Manage properties</Text>
          <Ionicons name="chevron-forward" size={16} color={theme.colors.secondary} />
        </View>
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
    fontSize: 14,
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
  empty: { marginBottom: theme.spacing.lg },
  emptyIcon: {
    width: 44,
    height: 44,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  emptyTitle: {
    fontSize: 17,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
  },
  emptyBody: {
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 6,
    lineHeight: 20,
  },
});
