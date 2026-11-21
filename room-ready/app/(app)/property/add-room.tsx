import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useCreateRoom } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function AddRoomScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(ROUTE_ROLES.propertyAddRoom);
  if (guard) return guard;

  const { propertyId } = useLocalSearchParams<{ propertyId: string }>();
  const create = useCreateRoom();
  const [form, setForm] = useState({
    name: '',
    floor: '',
    rentPcm: '',
    deposit: '',
    sizeSqm: '',
    furnished: false,
    ensuite: false,
  });

  function update(key: string, value: string | boolean) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit() {
    if (!propertyId || !form.name.trim()) {
      Alert.alert('Missing fields', 'Enter a room name');
      return;
    }
    try {
      await create.mutateAsync({
        propertyId,
        name: form.name.trim(),
        floor: form.floor.trim() || undefined,
        rentPcm: parseInt(form.rentPcm, 10) || 0,
        deposit: parseInt(form.deposit, 10) || 0,
        sizeSqm: parseFloat(form.sizeSqm) || undefined,
        furnished: form.furnished,
        ensuite: form.ensuite,
        status: 'available',
      });
      router.back();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not add room');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <Text style={styles.title}>Add room</Text>

      <Input label="Room name" value={form.name} onChangeText={(value) => update('name', value)} placeholder="Room name" />
      <Input label="Floor" value={form.floor} onChangeText={(value) => update('floor', value)} placeholder="Optional" />
      <Input label="Rent per month (£)" value={form.rentPcm} onChangeText={(value) => update('rentPcm', value)} keyboardType="number-pad" placeholder="0" />
      <Input label="Deposit (£)" value={form.deposit} onChangeText={(value) => update('deposit', value)} keyboardType="number-pad" placeholder="0" />
      <Input label="Floor area (m²)" value={form.sizeSqm} onChangeText={(value) => update('sizeSqm', value)} keyboardType="decimal-pad" placeholder="0" />

      <Text style={styles.label}>Furnished</Text>
      <View style={styles.row}>
        {[true, false].map((value) => (
          <Pressable key={String(value)} onPress={() => update('furnished', value)} style={[styles.chip, form.furnished === value && styles.chipSelected]}>
            <Text style={[styles.chipText, form.furnished === value && styles.chipTextSelected]}>{value ? 'Yes' : 'No'}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>Ensuite</Text>
      <View style={styles.row}>
        {[true, false].map((value) => (
          <Pressable key={`ensuite-${String(value)}`} onPress={() => update('ensuite', value)} style={[styles.chip, form.ensuite === value && styles.chipSelected]}>
            <Text style={[styles.chipText, form.ensuite === value && styles.chipTextSelected]}>{value ? 'Yes' : 'No'}</Text>
          </Pressable>
        ))}
      </View>

      <Button title="Add room" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  back: { flexDirection: 'row', alignItems: 'center', marginBottom: theme.spacing.md, alignSelf: 'flex-start' },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  title: { fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.lg },
  label: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.sm },
  row: { flexDirection: 'row', gap: 8, marginBottom: theme.spacing.md },
  chip: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: theme.radius.full, borderWidth: 1, borderColor: theme.colors.border },
  chipSelected: { backgroundColor: theme.colors.secondaryDark, borderColor: theme.colors.secondaryDark },
  chipText: { fontSize: 14, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  chipTextSelected: { color: theme.colors.textInverse, fontFamily: FONT_SEMIBOLD },
});
