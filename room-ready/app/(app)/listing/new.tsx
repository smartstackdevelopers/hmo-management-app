import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useCreateListing, useProperty } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function NewListingScreen() {
  const guard = useRoleGuard(ROUTE_ROLES.listingNew);
  if (guard) return guard;

  const { roomId, propertyId } = useLocalSearchParams<{ roomId: string; propertyId?: string }>();
  const { data, isLoading } = useProperty(propertyId ?? '');
  const create = useCreateListing();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [billsIncluded, setBillsIncluded] = useState(true);
  const [status, setStatus] = useState<'draft' | 'active'>('active');
  const qualityScore = getListingQualityScore(title, description, billsIncluded);

  const room = data?.property?.rooms?.find((r) => r.id === roomId);

  if (propertyId && isLoading) return <LoadingScreen />;

  async function handleSubmit() {
    if (!roomId || !title.trim()) {
      Alert.alert('Missing fields', 'Please enter a listing title');
      return;
    }
    try {
      const { listing } = await create.mutateAsync({
        roomId,
        title,
        description: description || undefined,
        billsIncluded,
        status,
        availableFrom: new Date().toISOString(),
      }) as { listing: { id: string } };
      router.replace(`/(app)/listing/${listing.id}`);
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not create listing');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      {room && (
        <View style={styles.roomCard}>
          <Text style={styles.roomInfo}>
            Listing for {room.name} · £{room.rentPcm}/pcm
          </Text>
          <Text style={styles.roomHint}>Write a clear, specific listing that builds confidence for prospective tenants.</Text>
        </View>
      )}

      <Input label="Title *" value={title} onChangeText={setTitle} placeholder="Bright ensuite room in Edgbaston HMO" />
      <Input label="Description" value={description} onChangeText={setDescription} multiline numberOfLines={4} placeholder="Describe the room, bills, location..." />
      <View style={styles.scoreCard}>
        <View style={styles.scoreTop}>
          <Text style={styles.scoreLabel}>Listing quality score</Text>
          <Text style={styles.scoreValue}>{qualityScore}%</Text>
        </View>
        <View style={styles.scoreMeter}>
          <View style={[styles.scoreFill, { width: `${qualityScore}%` }]} />
        </View>
        <View style={styles.scoreTipRow}>
          <Ionicons name="sparkles-outline" size={16} color={theme.colors.secondary} />
          <Text style={styles.scoreTip}>
            {qualityScore >= 80
              ? 'Excellent. This should convert well.'
              : 'Add a specific location, room features, and ideal tenant profile to improve conversions.'}
          </Text>
        </View>
      </View>

      <Text style={styles.label}>Bills included?</Text>
      <View style={styles.row}>
        {[true, false].map((v) => (
          <Pressable key={String(v)} onPress={() => setBillsIncluded(v)} style={[styles.chip, billsIncluded === v && styles.chipSelected]}>
            <Text style={[styles.chipText, billsIncluded === v && styles.chipTextSelected]}>{v ? 'Yes' : 'No'}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>Status</Text>
      <View style={styles.row}>
        {(['active', 'draft'] as const).map((s) => (
          <Pressable key={s} onPress={() => setStatus(s)} style={[styles.chip, status === s && styles.chipSelected]}>
            <Text style={[styles.chipText, status === s && styles.chipTextSelected]}>{s}</Text>
          </Pressable>
        ))}
      </View>

      <Button title="Create Listing" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  roomInfo: { color: theme.colors.secondary, fontWeight: '600', marginBottom: theme.spacing.lg },
  roomCard: {
    backgroundColor: theme.colors.infoLight,
    borderWidth: 1,
    borderColor: theme.colors.info,
    borderRadius: theme.radius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.lg,
  },
  roomHint: { color: theme.colors.textSecondary, fontSize: 13, lineHeight: 18, marginTop: 6 },
  label: { ...theme.typography.label, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.md },
  scoreCard: { marginTop: 6, marginBottom: theme.spacing.md, backgroundColor: theme.colors.surface, borderRadius: theme.radius.md, borderWidth: 1, borderColor: theme.colors.border, padding: theme.spacing.md },
  scoreTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  scoreLabel: { color: theme.colors.text, fontWeight: '600' },
  scoreValue: { color: theme.colors.secondary, fontWeight: '800' },
  scoreMeter: { height: 8, backgroundColor: theme.colors.borderLight, borderRadius: theme.radius.full, marginTop: 10, overflow: 'hidden' },
  scoreFill: { height: '100%', backgroundColor: theme.colors.secondary },
  scoreTipRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, marginTop: 10 },
  scoreTip: { color: theme.colors.textSecondary, fontSize: 13, flex: 1, lineHeight: 18 },
  row: { flexDirection: 'row', gap: 8, marginBottom: theme.spacing.md },
  chip: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: theme.radius.full, borderWidth: 1, borderColor: theme.colors.border },
  chipSelected: { backgroundColor: theme.colors.secondary, borderColor: theme.colors.secondary },
  chipText: { fontSize: 14, color: theme.colors.textSecondary, textTransform: 'capitalize' },
  chipTextSelected: { color: theme.colors.textInverse, fontWeight: '600' },
});

function getListingQualityScore(title: string, description: string, billsIncluded: boolean): number {
  let score = 25;
  if (title.trim().length >= 20) score += 20;
  if (description.trim().length >= 80) score += 30;
  if (description.toLowerCase().includes('station') || description.toLowerCase().includes('transport')) score += 10;
  if (description.toLowerCase().includes('ensuite') || description.toLowerCase().includes('furnished')) score += 10;
  if (billsIncluded) score += 5;
  return Math.min(score, 100);
}
