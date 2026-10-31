import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text } from 'react-native';

import { CouncilStandardsBanner } from '@/components/compliance/CouncilStandardsBanner';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { BIRMINGHAM_COUNCIL, HMO_ROOM_STANDARDS } from '@/constants/birmingham';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useCreateProperty } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function NewPropertyScreen() {
  const guard = useRoleGuard(ROUTE_ROLES.propertyNew);
  if (guard) return guard;

  const create = useCreateProperty();
  const [form, setForm] = useState({
    name: '',
    addressLine1: '',
    city: 'Birmingham',
    postcode: '',
    hmoLicenceNumber: '',
    maxOccupants: '5',
    description: '',
    emergencyContact: '',
    houseRules: 'Bin collection: refer to Birmingham City Council schedule. No smoking indoors. Quiet hours 11pm–7am.',
  });

  function update(key: string, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit() {
    if (!form.name || !form.addressLine1 || !form.city || !form.postcode) {
      Alert.alert('Missing fields', 'Please complete all required fields');
      return;
    }
    try {
      const result = await create.mutateAsync({
        name: form.name,
        addressLine1: form.addressLine1,
        city: form.city,
        postcode: form.postcode.toUpperCase(),
        hmoLicenceNumber: form.hmoLicenceNumber || undefined,
        maxOccupants: parseInt(form.maxOccupants, 10) || 0,
        description: form.description || undefined,
        emergencyContact: form.emergencyContact || undefined,
        houseRules: form.houseRules || undefined,
      }) as { property: { id: string } };
      const newId = result.property.id;
      Alert.alert('Property created', 'Add rooms to complete your HMO setup.', [
        { text: 'Done', onPress: () => router.replace(`/(app)/property/${newId}`) },
        {
          text: 'Add Room',
          onPress: () => router.replace({ pathname: '/(app)/property/add-room', params: { propertyId: newId } }),
        },
      ]);
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Failed to create property');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <CouncilStandardsBanner variant="compact" />

      <Text style={styles.hint}>
        Register a new HMO property for {BIRMINGHAM_COUNCIL.city}. Mandatory licence required for 5+ occupants forming 2+ households.
      </Text>

      <Card style={styles.standardsCard}>
        <Text style={styles.standardsTitle}>Room size minimums</Text>
        <Text style={styles.standardsBody}>
          Single: {HMO_ROOM_STANDARDS.singleOccupancy}m² · Double: {HMO_ROOM_STANDARDS.doubleOccupancy}m²
        </Text>
      </Card>

      <Input label="Property name *" value={form.name} onChangeText={(v) => update('name', v)} placeholder="42 Edgbaston Road HMO" />
      <Input label="Address line 1 *" value={form.addressLine1} onChangeText={(v) => update('addressLine1', v)} placeholder="42 Edgbaston Road" />
      <Input label="City *" value={form.city} onChangeText={(v) => update('city', v)} placeholder="Birmingham" />
      <Input label="Postcode *" value={form.postcode} onChangeText={(v) => update('postcode', v)} placeholder="B15 2TT" autoCapitalize="characters" />
      <Input
        label="HMO licence number *"
        value={form.hmoLicenceNumber}
        onChangeText={(v) => update('hmoLicenceNumber', v)}
        placeholder="HMO-BCC-2025-0042"
      />
      <Input label="Max occupants (licence)" value={form.maxOccupants} onChangeText={(v) => update('maxOccupants', v)} keyboardType="number-pad" />
      <Input label="Description" value={form.description} onChangeText={(v) => update('description', v)} multiline numberOfLines={3} />
      <Input
        label="Responsible person / emergency contact *"
        value={form.emergencyContact}
        onChangeText={(v) => update('emergencyContact', v)}
        placeholder="James Mitchell: 07700 900123"
      />
      <Input label="House rules & waste arrangements" value={form.houseRules} onChangeText={(v) => update('houseRules', v)} multiline numberOfLines={4} />
      <Button title="Create Property" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
      <Text style={styles.footer}>Contact {BIRMINGHAM_COUNCIL.licensingEmail} for licensing enquiries</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  hint: { color: theme.colors.textSecondary, marginBottom: theme.spacing.md, lineHeight: 20 },
  standardsCard: { marginBottom: theme.spacing.lg, backgroundColor: theme.colors.surfaceSecondary },
  standardsTitle: { fontWeight: '700', color: theme.colors.text, fontSize: 14 },
  standardsBody: { fontSize: 13, color: theme.colors.textSecondary, marginTop: 4 },
  footer: { textAlign: 'center', fontSize: 12, color: theme.colors.textMuted, marginTop: theme.spacing.md },
});
