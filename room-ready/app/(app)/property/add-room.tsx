import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { HMO_ROOM_STANDARDS } from '@/constants/birmingham';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useCreateRoom } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function AddRoomScreen() {
  const guard = useRoleGuard(ROUTE_ROLES.propertyAddRoom);
  if (guard) return guard;

  const { propertyId } = useLocalSearchParams<{ propertyId: string }>();
  const create = useCreateRoom();
  const [form, setForm] = useState({
    name: '',
    floor: 'Ground',
    rentPcm: '550',
    deposit: '600',
    sizeSqm: '12',
    furnished: true,
    ensuite: false,
  });

  function update(key: string, value: string | boolean) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit() {
    if (!propertyId || !form.name) {
      Alert.alert('Missing fields', 'Please enter a room name');
      return;
    }
    try {
      await create.mutateAsync({
        propertyId,
        name: form.name,
        floor: form.floor,
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
      <Text style={styles.hint}>
        BCC minimum: {HMO_ROOM_STANDARDS.singleOccupancy}m² single · {HMO_ROOM_STANDARDS.doubleOccupancy}m² double
      </Text>
      <Input label="Room name *" value={form.name} onChangeText={(v) => update('name', v)} placeholder="Room 1 - Ground" />
      <Input label="Floor" value={form.floor} onChangeText={(v) => update('floor', v)} placeholder="Ground" />
      <Input label="Rent pcm (£)" value={form.rentPcm} onChangeText={(v) => update('rentPcm', v)} keyboardType="number-pad" />
      <Input label="Deposit (£)" value={form.deposit} onChangeText={(v) => update('deposit', v)} keyboardType="number-pad" />
      <Input label="Floor area (m²)" value={form.sizeSqm} onChangeText={(v) => update('sizeSqm', v)} keyboardType="decimal-pad" />

      <Text style={styles.label}>Furnished</Text>
      <View style={styles.row}>
        {[true, false].map((v) => (
          <Pressable key={String(v)} onPress={() => update('furnished', v)} style={[styles.chip, form.furnished === v && styles.chipSelected]}>
            <Text style={[styles.chipText, form.furnished === v && styles.chipTextSelected]}>{v ? 'Yes' : 'No'}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>Ensuite</Text>
      <View style={styles.row}>
        {[true, false].map((v) => (
          <Pressable key={String(v)} onPress={() => update('ensuite', v)} style={[styles.chip, form.ensuite === v && styles.chipSelected]}>
            <Text style={[styles.chipText, form.ensuite === v && styles.chipTextSelected]}>{v ? 'Yes' : 'No'}</Text>
          </Pressable>
        ))}
      </View>

      <Button title="Add Room" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  hint: { color: theme.colors.textSecondary, marginBottom: theme.spacing.lg, lineHeight: 20, fontSize: 13 },
  label: { ...theme.typography.label, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.md },
  row: { flexDirection: 'row', gap: 8, marginBottom: theme.spacing.md },
  chip: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: theme.radius.full, borderWidth: 1, borderColor: theme.colors.border },
  chipSelected: { backgroundColor: theme.colors.secondary, borderColor: theme.colors.secondary },
  chipText: { fontSize: 14, color: theme.colors.textSecondary },
  chipTextSelected: { color: theme.colors.textInverse, fontWeight: '600' },
});
