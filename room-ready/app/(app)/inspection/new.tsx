import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useCreateInspection, useProperties } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function NewInspectionScreen() {
  useHideTabHeader();
  const guard = useRoleGuard([...ROUTE_ROLES.inspectionNew, 'landlord']);
  if (guard) return guard;

  const { data, isLoading } = useProperties();
  const create = useCreateInspection();
  const [propertyId, setPropertyId] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [notes, setNotes] = useState('');

  if (isLoading) return <LoadingScreen />;

  const properties = data?.properties ?? [];

  async function handleSubmit() {
    if (!propertyId || !date.trim()) {
      Alert.alert('Missing fields', 'Choose a property and a date');
      return;
    }
    const [day, month, year] = date.split('/').map(Number);
    const [hours, minutes] = (time || '00:00').split(':').map(Number);
    if (!day || !month || !year) {
      Alert.alert('Invalid date', 'Use DD/MM/YYYY');
      return;
    }
    const scheduledAt = new Date(year, month - 1, day, hours || 0, minutes || 0);
    if (Number.isNaN(scheduledAt.getTime())) {
      Alert.alert('Invalid date', 'Use DD/MM/YYYY');
      return;
    }
    try {
      await create.mutateAsync({
        propertyId,
        scheduledAt: scheduledAt.toISOString(),
        notes: notes.trim() || undefined,
      });
      router.back();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not schedule inspection');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <Text style={styles.title}>Schedule inspection</Text>

      <Text style={styles.label}>Property</Text>
      {properties.length === 0 ? <Text style={styles.empty}>No properties to schedule against.</Text> : null}
      {properties.map((property) => {
        const selected = propertyId === property.id;
        const label = property.addressLine1 || property.name;
        return (
          <Pressable
            key={property.id}
            onPress={() => setPropertyId(property.id)}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            style={[styles.option, selected && styles.optionSelected]}
          >
            <Text style={styles.optionText}>{label}</Text>
            <Text style={styles.optionMeta}>{property.postcode}</Text>
          </Pressable>
        );
      })}

      <Input label="Date" value={date} onChangeText={setDate} placeholder="DD/MM/YYYY" />
      <Input label="Time" value={time} onChangeText={setTime} placeholder="HH:MM" />
      <Input label="Notes" value={notes} onChangeText={setNotes} multiline numberOfLines={3} placeholder="Optional" />
      <Button title="Schedule" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  back: { flexDirection: 'row', alignItems: 'center', marginBottom: theme.spacing.md, alignSelf: 'flex-start' },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  title: { fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.lg },
  label: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: theme.spacing.sm },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  option: { padding: 12, borderRadius: theme.radius.md, borderWidth: 1, borderColor: theme.colors.border, marginBottom: 8, backgroundColor: theme.colors.surface },
  optionSelected: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.accentLight },
  optionText: { color: theme.colors.text, fontFamily: FONT_SEMIBOLD },
  optionMeta: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2, fontFamily: FONT_MEDIUM },
});
