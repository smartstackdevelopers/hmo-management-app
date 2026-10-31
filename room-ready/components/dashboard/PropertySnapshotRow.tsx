import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { theme } from '@/constants/theme';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { PropertyItem } from '@/lib/api';
import { assessPropertyCompliance } from '@/lib/compliance';
import { propertyCoverUrl } from '@/lib/propertyCovers';

interface PropertySnapshotRowProps {
  properties: PropertyItem[];
}

export function PropertySnapshotRow({ properties }: PropertySnapshotRowProps) {
  const shown = properties.slice(0, 6);
  if (!shown.length) return null;

  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Text style={styles.title}>Your properties</Text>
        <Pressable onPress={() => router.push('/(app)/(tabs)/properties')} hitSlop={8}>
          <Text style={styles.action}>See all</Text>
        </Pressable>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        {shown.map((property) => {
          const report = assessPropertyCompliance(property);
          const occupied = property.rooms?.filter((r) => r.status === 'occupied').length ?? 0;
          const total = property.rooms?.length ?? 0;
          const scoreTone =
            report.score >= 85 ? theme.colors.success : report.score >= 60 ? theme.colors.warning : theme.colors.error;

          return (
            <Pressable
              key={property.id}
              style={({ pressed }) => [styles.card, pressed && styles.pressed]}
              onPress={() => router.push(`/(app)/property/${property.id}`)}
            >
              <Image source={{ uri: propertyCoverUrl(property.id) }} style={styles.cover} />
              <View style={styles.cardBody}>
                <View style={[styles.scoreBadge, { backgroundColor: `${scoreTone}18` }]}>
                  <Text style={[styles.scoreText, { color: scoreTone }]}>{report.score}%</Text>
                </View>
                <Text style={styles.name} numberOfLines={2}>{property.name}</Text>
                <Text style={styles.meta} numberOfLines={1}>
                  {occupied}/{total} rooms · {property.postcode}
                </Text>
              </View>
            </Pressable>
          );
        })}
        <Pressable
          style={({ pressed }) => [styles.addCard, pressed && styles.pressed]}
          onPress={() => router.push('/(app)/property/new')}
        >
          <Ionicons name="add" size={24} color={theme.colors.secondary} />
          <Text style={styles.addLabel}>Add property</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.lg },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm,
  },
  title: {
    fontSize: 17,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.2,
  },
  action: { fontSize: 14, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.secondary },
  scroll: { gap: theme.spacing.sm, paddingRight: theme.spacing.md },
  card: {
    width: 168,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    overflow: 'hidden',
  },
  pressed: { opacity: 0.92 },
  cover: { width: '100%', height: 88, backgroundColor: theme.colors.surfaceMuted },
  cardBody: { padding: 12 },
  scoreBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: theme.radius.full,
    marginBottom: 8,
  },
  scoreText: { fontSize: 12, fontFamily: FONT_BOLD, fontWeight: '700' },
  name: {
    fontSize: 14,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    lineHeight: 18,
    minHeight: 36,
  },
  meta: { fontSize: 12, color: theme.colors.textSecondary, marginTop: 4, fontFamily: FONT_MEDIUM },
  addCard: {
    width: 120,
    padding: theme.spacing.md,
    backgroundColor: theme.colors.accentLight,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  addLabel: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.secondary,
    textAlign: 'center',
  },
});
