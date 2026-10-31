import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useCreateInspection, useProperties } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function NewInspectionScreen() {
  const guard = useRoleGuard(ROUTE_ROLES.inspectionNew);
  if (guard) return guard;

  const { data, isLoading } = useProperties();
  const create = useCreateInspection();
  const [propertyId, setPropertyId] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('10:00');
  const [notes, setNotes] = useState('');

  if (isLoading) return <LoadingScreen />;

  const properties = data?.properties ?? [];

  async function handleSubmit() {
    if (!propertyId || !date) {
      Alert.alert('Missing fields', 'Select a property and date');
      return;
    }
    const [day, month, year] = date.split('/').map(Number);
    const [hours, minutes] = time.split(':').map(Number);
    if (!day || !month || !year) {
      Alert.alert('Invalid date', 'Use DD/MM/YYYY format');
      return;
    }
    const scheduledAt = new Date(year, month - 1, day, hours || 10, minutes || 0);
    try {
      await create.mutateAsync({
        propertyId,
        scheduledAt: scheduledAt.toISOString(),
        notes: notes || undefined,
      });
      router.back();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not schedule inspection');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.hint}>Schedule a compliance inspection for a managed property.</Text>

      <Text style={styles.label}>Property *</Text>
      {properties.map((p) => (
        <Pressable
          key={p.id}
          onPress={() => setPropertyId(p.id)}
          style={[styles.option, propertyId === p.id && styles.optionSelected]}
        >
          <Text style={styles.optionText}>{p.name}</Text>
          <Text style={styles.optionMeta}>{p.postcode}</Text>
        </Pressable>
      ))}

      <Input label="Date (DD/MM/YYYY) *" value={date} onChangeText={setDate} placeholder="15/08/2026" />
      <Input label="Time (HH:MM)" value={time} onChangeText={setTime} placeholder="10:00" />
      <Input label="Notes" value={notes} onChangeText={setNotes} multiline numberOfLines={3} placeholder="Quarterly HMO compliance check..." />
      <Button title="Schedule Inspection" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  hint: { color: theme.colors.textSecondary, marginBottom: theme.spacing.lg, lineHeight: 20 },
  label: { ...theme.typography.label, color: theme.colors.text, marginBottom: theme.spacing.sm, marginTop: theme.spacing.md },
  option: { padding: 12, borderRadius: theme.radius.md, borderWidth: 1, borderColor: theme.colors.border, marginBottom: 8 },
  optionSelected: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.infoLight },
  optionText: { color: theme.colors.text, fontWeight: '600' },
  optionMeta: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2 },
});
