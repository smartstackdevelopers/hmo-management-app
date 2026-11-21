import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useCreateListing, useProperty } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function NewListingScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(ROUTE_ROLES.listingNew);
  if (guard) return guard;

  const { roomId, propertyId } = useLocalSearchParams<{ roomId: string; propertyId?: string }>();
  const { data, isLoading } = useProperty(propertyId ?? '');
  const create = useCreateListing();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [billsIncluded, setBillsIncluded] = useState(true);
  const [status, setStatus] = useState<'draft' | 'active'>('active');

  const room = data?.property?.rooms?.find((item) => item.id === roomId);
  if (propertyId && isLoading) return <LoadingScreen />;

  async function handleSubmit() {
    if (!roomId || !title.trim()) {
      Alert.alert('Missing fields', 'Enter a listing title');
      return;
    }
    try {
      const { listing } = await create.mutateAsync({
        roomId,
        title: title.trim(),
        description: description.trim() || undefined,
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
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <Text style={styles.title}>Create listing</Text>
      {room ? (
        <Text style={styles.hint}>
          {room.name}
          {room.rentPcm ? ` · £${room.rentPcm} / month` : ''}
        </Text>
      ) : null}

      <Input label="Title" value={title} onChangeText={setTitle} placeholder="Listing title" />
      <Input label="Description" value={description} onChangeText={setDescription} multiline numberOfLines={4} placeholder="Optional" />

      <Text style={styles.label}>Bills included</Text>
      <View style={styles.row}>
        {[true, false].map((value) => (
          <Pressable key={String(value)} onPress={() => setBillsIncluded(value)} style={[styles.chip, billsIncluded === value && styles.chipSelected]}>
            <Text style={[styles.chipText, billsIncluded === value && styles.chipTextSelected]}>{value ? 'Yes' : 'No'}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>Status</Text>
      <View style={styles.row}>
        {(['active', 'draft'] as const).map((value) => (
          <Pressable key={value} onPress={() => setStatus(value)} style={[styles.chip, status === value && styles.chipSelected]}>
            <Text style={[styles.chipText, status === value && styles.chipTextSelected]}>{value === 'active' ? 'Active' : 'Draft'}</Text>
          </Pressable>
        ))}
      </View>

      <Button title="Create listing" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  back: { flexDirection: 'row', alignItems: 'center', marginBottom: theme.spacing.md, alignSelf: 'flex-start' },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  title: { fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4 },
  hint: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 8, marginBottom: theme.spacing.md },
  label: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.sm },
  row: { flexDirection: 'row', gap: 8, marginBottom: theme.spacing.md },
  chip: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: theme.radius.full, borderWidth: 1, borderColor: theme.colors.border },
  chipSelected: { backgroundColor: theme.colors.secondaryDark, borderColor: theme.colors.secondaryDark },
  chipText: { fontSize: 14, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  chipTextSelected: { color: theme.colors.textInverse, fontFamily: FONT_SEMIBOLD },
});
